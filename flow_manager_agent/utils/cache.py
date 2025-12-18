import json
from datetime import datetime, timezone, timedelta
from google.cloud import bigquery
import logging

logger = logging.getLogger(__name__)


# ============================================================
# Normalization helpers לאינטנט (כמו שהיה אצלך)
# ============================================================
def _normalize_numbers(obj):
    """
    מעבר רקורסיבי על כל ה-JSON:
    - "3" -> 3
    - רץ גם על dict וגם על list
    """
    if isinstance(obj, dict):
        return {k: _normalize_numbers(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [_normalize_numbers(x) for x in obj]

    if isinstance(obj, str):
        s = obj.strip()
        if s.isdigit():
            return int(s)
        return s

    return obj


def normalize_intent_key(
    parsed_intent: dict | None = None,
    user_message: str | None = None,
    sql: str | None = None,
    default_scope: str = "time_bounded",
) -> str:
    """
    בונה intent_key יציב ואחיד.

    כללים:
    - אם יש SQL → משתמשים בו כמפתח (הכי ייחודי ודטרמיניסטי)
    - אחרת אם יש parsed_intent (dict):
        * לוודא שקיים שדה 'scope' ושאינו None/ריק.
        * אם חסר / None / "" / [] → scope = default_scope ("time_bounded").
        * להריץ _normalize_numbers כדי שמספרים כטקסט יהיו מספרים אמיתיים.
        * מחזירים JSON מנורמל עם sort_keys=True.
    - אחרת נופלים ל-user_message, אם קיים.
    - אחרת מחזירים מחרוזת ריקה.
    """

    # עדיפות ראשונה: SQL (הכי ייחודי)
    if sql and sql.strip():
        # נרמול SQL: הסרת רווחים מיותרים ושורות חדשות
        normalized_sql = " ".join(sql.strip().split())
        return normalized_sql

    # עדיפות שנייה: parsed_intent
    base = parsed_intent or {}
    if isinstance(base, dict) and base:
        # עושים עותק כדי לא לגעת באובייקט המקורי
        normalized = dict(base)

        # scope ברירת מחדל
        scope = normalized.get("scope")
        if scope in (None, "", []):
            normalized["scope"] = default_scope

        # המרת "3" → 3 וכו'
        normalized = _normalize_numbers(normalized)

        return json.dumps(normalized, sort_keys=True, ensure_ascii=False).strip()

    # עדיפות שלישית: user_message
    if user_message and user_message.strip():
        return user_message.strip()

    return ""


# ============================================================
# Cache Service עם use_count + TTL
# ============================================================
class CacheService:
    """
    Cache מבוסס BigQuery.
    טבלה: practicode-2025.cache.cached_queries

    שדות חובה בטבלה:
      intent_key   (STRING)
      sql          (STRING)
      result       (STRING, nullable)
      last_updated (TIMESTAMP)
      use_count    (INT64)
    """

    # כמה זמן התוצאה שנשמרה בקאש נחשבת תקפה
    TTL = timedelta(seconds=30)

    def __init__(self):
        self.project = "practicode-2025"
        self.dataset = "cache"
        self.table = "cached_queries"
        self.client = bigquery.Client(project=self.project, location="EU")

    # -------------------------------------------------------
    # קריאה ישירה מה-Cache לפי intent_key (לשימוש כללי)
    # -------------------------------------------------------
    def get_by_intent(self, intent_key: str):
        return self._load_entry(intent_key)

    # -------------------------------------------------------
    # 🔹 פונקציה מיוחדת ל-RootAgent:
    #    מחזירה תוצאה רק אם:
    #      - יש result בקאש
    #      - ה-TTL לא פג
    # -------------------------------------------------------
    def get_valid_cached_result(self, intent_key: str):
        """
        מחזירה:
            {
              "rows": [...],
              "executed_sql": "...",
              "row_count": N,
            }
        או None אם:
          - אין רשומה
          - אין result
          - TTL פג
          - ה-JSON ב-result שבור
        """
        entry = self._load_entry(intent_key)
        if not entry:
            return None

        result_json = entry.get("result")
        if not result_json:
            # עדיין לא הגענו לשימוש השלישי → אין תוצאה שמורה
            return None

        last_updated = entry.get("last_updated")
        if not last_updated:
            return None

        if last_updated.tzinfo is None:
            last_updated = last_updated.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        if (now - last_updated) > self.TTL:
            # תוצאה ישנה מדי → לא להשתמש בקאש
            return None

        try:
            rows = json.loads(result_json)
        except Exception:
            return None

        executed_sql = entry.get("sql") or ""

        return {
            "rows": rows,
            "executed_sql": executed_sql,
            "row_count": len(rows),
        }

    # -------------------------------------------------------
    # הלב של הקאש – משמש את QueryExecutor
    # -------------------------------------------------------
    def run_query_with_cache(self, *, sql: str, intent_key: str, run_bigquery_fn):
        """
        לוגיקה משולבת use_count + TTL:

        ✔ שימוש 1–2:
           - תמיד מריצים BigQuery
           - מעדכנים use_count בלבד
           - לא שומרים result בקאש (result=NULL)

        ✔ שימוש 3:
           - מריצים BigQuery
           - שומרים result בקאש + last_updated
           - from_cache=False

        ✔ שימוש 4+:
           - אם יש result בקאש וה-TTL בתוקף → מחזירים מהקאש (from_cache=True)
           - אם TTL פג / אין result / JSON שבור → מריצים BigQuery ומעדכנים result
        """

        entry = self._load_entry(intent_key)
        now = datetime.now(timezone.utc)

        # -------------------------
        # 1) אין רשומה בכלל → יצירה ראשונית
        # -------------------------
        if entry is None:
            # יצירת רשומה חדשה:
            #   use_count = 1
            #   result = NULL
            logger.info(f"[CACHE] New entry - creating with use_count=1 for key: {intent_key[:50]}...")
            self._insert_new_entry(intent_key, sql, now)

            # מריצים BigQuery אבל לא שומרים result בקאש
            result = run_bigquery_fn(sql)
            safe = self._make_json_safe(result)
            return safe, False

        # -------------------------
        # 2) רשומה קיימת
        # -------------------------
        current_count = int(entry.get("use_count") or 0)
        use_count = current_count + 1
        logger.info(f"[CACHE] Existing entry - use_count: {current_count} -> {use_count} for key: {intent_key[:50]}...")

        result_json = entry.get("result")
        has_result = bool(result_json)

        last_updated = entry.get("last_updated")
        if last_updated is not None and last_updated.tzinfo is None:
            last_updated = last_updated.replace(tzinfo=timezone.utc)

        # TTL רלוונטי רק אם יש result
        is_expired = False
        if has_result:
            if last_updated is None:
                is_expired = True
            else:
                is_expired = (now - last_updated) > self.TTL

        # -------------------------
        # 2.א) שימושים 1–2 → רק חימום
        # -------------------------
        if use_count < 3:
            logger.info(f"[CACHE] Warming up - updating use_count to {use_count} (no result saved yet)")
            # מעדכנים רק use_count, לא נוגעים ב-last_updated ולא ב-result
            self._update_use_count(intent_key, use_count)

            result = run_bigquery_fn(sql)
            safe = self._make_json_safe(result)
            return safe, False

        # -------------------------
        # 2.ב) שימוש 3 → מחשבים ושומרים לקאש
        # -------------------------
        if use_count == 3:
            logger.info(f"[CACHE] 3rd use! Running BQ and saving result to cache")
            result = run_bigquery_fn(sql)
            safe = self._make_json_safe(result)

            # כאן בפעם הראשונה נשמר result + last_updated + use_count=3
            self._update_result(
                intent_key=intent_key,
                result=safe,
                sql=sql,
                now=now,
                use_count=use_count,
            )

            return safe, False

        # -------------------------
        # 2.ג) שימוש 4+ → כבר אמור להיות result בקאש
        # -------------------------
        if has_result and not is_expired:
            logger.info(f"[CACHE] Cache HIT! Returning from cache (use_count: {use_count}, TTL valid)")
            # TTL בתוקף → מחזירים מהקאש בלבד
            self._update_use_count(intent_key, use_count)
            try:
                rows = json.loads(result_json)
                return rows, True
            except Exception:
                logger.warning(f"[CACHE] JSON parse error, recomputing")
                # JSON שבור → נופלים ל-recompute
                pass

        # אם הגענו לכאן:
        #   - או שאין result (לא אמור לקרות אחרי שימוש 3)
        #   - או שה-TTL פג
        #   - או ש-JSON שבור
        logger.info(f"[CACHE] Cache MISS or TTL expired - running BQ and refreshing cache")
        result = run_bigquery_fn(sql)
        safe = self._make_json_safe(result)

        self._update_result(
            intent_key=intent_key,
            result=safe,
            sql=sql,
            now=now,
            use_count=use_count,
        )

        return safe, False

    # -------------------------------------------------------
    # INTERNAL HELPERS
    # -------------------------------------------------------
    def _load_entry(self, intent_key: str):
        """טוען רשומה מלאה לפי intent_key."""
        query = f"""
            SELECT intent_key, sql, result, last_updated, use_count
            FROM `{self.project}.{self.dataset}.{self.table}`
            WHERE intent_key = @key
            ORDER BY last_updated DESC
            LIMIT 1
        """

        job = self.client.query(
            query,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("key", "STRING", intent_key)
                ]
            ),
        )

        rows = list(job)
        return dict(rows[0]) if rows else None

    def _insert_new_entry(self, intent_key: str, sql: str, now: datetime):
        """מכניס רשומה חדשה עם use_count=1 ו-result=NULL באמצעות MERGE."""
        # Using MERGE instead of INSERT to handle race conditions
        merge_sql = f"""
            MERGE `{self.project}.{self.dataset}.{self.table}` T
            USING (SELECT @key AS intent_key, @sql AS sql, CAST(NULL AS STRING) AS result, @ts AS last_updated, @cnt AS use_count) S
            ON T.intent_key = S.intent_key
            WHEN NOT MATCHED THEN
              INSERT (intent_key, sql, result, last_updated, use_count)
              VALUES (S.intent_key, S.sql, S.result, S.last_updated, S.use_count)
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("key", "STRING", intent_key),
                bigquery.ScalarQueryParameter("sql", "STRING", sql),
                bigquery.ScalarQueryParameter("ts", "TIMESTAMP", now.isoformat()),
                bigquery.ScalarQueryParameter("cnt", "INT64", 1),
            ]
        )

        self.client.query(merge_sql, job_config=job_config).result()

    def _update_use_count(self, intent_key: str, new_count: int):
        """
        מעדכן רק use_count באופן אטומי.
        בכוונה *לא* נוגע ב-last_updated, כדי ש-TTL יהיה לפי זמן חישוב ה-result,
        ולא לפי כמות הפעמים ששאלו.
        """
        logger.info(f"[CACHE] Atomically incrementing use_count to {new_count} for key: {intent_key[:50]}...")
        
        # Use atomic increment to avoid race conditions
        update_sql = f"""
            UPDATE `{self.project}.{self.dataset}.{self.table}`
            SET use_count = use_count + 1
            WHERE intent_key = @key
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("key", "STRING", intent_key),
            ]
        )

        job = self.client.query(update_sql, job_config=job_config)
        job.result()  # Wait for completion
        
        logger.info(f"[CACHE] Successfully incremented use_count")

    def _update_result(self, intent_key: str, result, sql: str, now: datetime, use_count: int):
        """שומר את התוצאה בקאש (וגם מעדכן sql, last_updated, use_count)."""
        json_string = json.dumps(result, ensure_ascii=False)

        update_sql = f"""
            UPDATE `{self.project}.{self.dataset}.{self.table}`
            SET
                result = @res,
                last_updated = @ts,
                sql = @sql,
                use_count = @cnt
            WHERE intent_key = @key
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("res", "STRING", json_string),
                bigquery.ScalarQueryParameter("ts", "TIMESTAMP", now.isoformat()),
                bigquery.ScalarQueryParameter("sql", "STRING", sql),
                bigquery.ScalarQueryParameter("cnt", "INT64", use_count),
                bigquery.ScalarQueryParameter("key", "STRING", intent_key),
            ]
        )

        self.client.query(update_sql, job_config=job_config).result()

    # -------------------------------------------------------
    def _make_json_safe(self, result_list):
        from datetime import datetime as _dt

        def fix(v):
            return v.isoformat() if isinstance(v, _dt) else v

        return [{k: fix(v) for k, v in row.items()} for row in result_list]
