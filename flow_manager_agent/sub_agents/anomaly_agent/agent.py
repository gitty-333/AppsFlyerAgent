from typing import AsyncGenerator
from pathlib import Path
import logging
import json

from pydantic import PrivateAttr
from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.genai import types

from AppsFlyerAgent.bq import BQClient

logger = logging.getLogger(__name__)


def _text_event(msg: str) -> Event:
    """Helper: convert plain text into ADK Event."""
    return Event(
        author="assistant",
        content=types.Content(parts=[types.Part(text=msg)])
    )


# --- SQL loading ---
BASE_DIR = Path(__file__).parent

SPIKE_SQL = (BASE_DIR / "queries" / "spike_clicks.sql").read_text(
    encoding="utf-8"
)
DROP_SQL = (BASE_DIR / "queries" / "drop_clicks.sql").read_text(
    encoding="utf-8"
)


class AnomalyAgent(BaseAgent):
    """
    ADK anomaly agent.

    - מריץ 2 שאילתות (spike + drop) ב-BigQuery
    - מזהה אנומליות (לפי השאילתות)
    - מחזיר JSON מסוכם ל-ADK Web
    """

    _client: BQClient = PrivateAttr()

    def __init__(self):
        super().__init__(name="anomaly_agent")
        self._client = BQClient()

    # ------------------------------------------------------------------ #
    #  BigQuery helpers
    # ------------------------------------------------------------------ #

    def pull_data(self):
        """
        מריץ את שאילתות ה-Spike וה-Drop ומחזיר DataFrames.
        """
        logger.info("[AnomalyAgent] Pulling anomaly data from BQ")

        spike_df = self._client.execute_query(
            SPIKE_SQL, "anomaly_spike"
        ).to_dataframe()

        # drop_df = self._client.execute_query(
        #     DROP_SQL, "anomaly_drop"
        # ).to_dataframe()

        return {"spike": spike_df}

    def get_spike_anomalies(self):
        """
        מחזיר DataFrame עם תוצאות השאילתה spike_clicks.sql.
        זה מיועד לשימוש חיצוני (למשל סקריפט גרפים), לא ל-ADK Web.
        """
        logger.info("[AnomalyAgent] Fetching spike anomalies (direct)")
        df = self._client.execute_query(
            SPIKE_SQL,
            "spike_anomalies_direct",
        ).to_dataframe()
        return df

    # ------------------------------------------------------------------ #
    #  Logic
    # ------------------------------------------------------------------ #

    def detect_anomalies(self, results):
        """
        Keep dataframes here; convert to JSON in report().
        results["spike"] / results["drop"] הם DataFrames.
        """
        anomalies = {}

        spike_df = results.get("spike")
        # drop_df = results.get("drop")

        if spike_df is not None and not spike_df.empty:
            anomalies["click_spike"] = spike_df

        # if drop_df is not None and not drop_df.empty:
        #     anomalies["click_drop"] = drop_df

        return anomalies

    def report(self, anomalies):
        """
        ממיר את ה-DataFrames ל-JSON אחיד:

        [
          {
            "name": "media_source_123",
            "anomaly_type": "click_spike" / "click_drop",
            "event_hour": 10,
            "clicks": 123,
            "avg_clicks": 50.5
          },
          ...
        ]

        תומך גם ב-spike_clicks.sql (עם hr + baseline_mean)
        וגם ב-drop_clicks.sql (עם event_hour + avg_clicks).
        """
        if not anomalies:
            return {
                "status": "ok",
                "message": "לא נמצאו אנומליות.",
                "anomalies": []
            }

        json_anomalies = []

        for name, df in anomalies.items():
            if df is None or df.empty:
                continue

            for _, row in df.iterrows():
                # ----- שעה -----
                if "event_hour" in df.columns:
                    event_hour = int(row["event_hour"])
                elif "hr" in df.columns:
                    event_hour = int(row["hr"])
                else:
                    event_hour = None

                # ----- קליקים -----
                if "clicks" in df.columns:
                    clicks = int(row["clicks"])
                elif "current_clicks" in df.columns:
                    clicks = int(row["current_clicks"])
                else:
                    clicks = None

                # ----- ממוצע (baseline / avg) -----
                if "avg_clicks" in df.columns:
                    avg_clicks = float(row["avg_clicks"])
                elif "baseline_mean" in df.columns:
                    avg_clicks = float(row["baseline_mean"])
                else:
                    avg_clicks = None

                json_anomalies.append({
                    "name": str(row.get("media_source", "")),
                    "anomaly_type": name,
                    "event_hour": event_hour,
                    "clicks": clicks,
                    "avg_clicks": avg_clicks,
                })

        summary = f"נמצאו {len(json_anomalies)} אנומליות."
        return {
            "status": "ok",
            "message": summary,
            "anomalies": json_anomalies
        }

    def run_daily(self):
        """
        פונקציה סינכרונית – מריץ BQ + זיהוי + יצירת JSON.
        (משמשת גם ב-ADK web בתוך _run_async_impl)
        """
        data = self.pull_data()
        anomalies = self.detect_anomalies(data)
        return self.report(anomalies)

    # ------------------------------------------------------------------ #
    #  ADK async interface
    # ------------------------------------------------------------------ #

    async def _run_async_impl(self, context) -> AsyncGenerator[Event, None]:
        """
        מה שנקרא מתוך RootAgent כשעושים אנומליה-flow ב-ADK web.
        """
        state = context.session.state

        res = self.run_daily()

        # לשמירה ב-state – כדי שתוכלי לראות ב-debug / להשתמש אח"כ
        state["anomaly_result"] = res

        # החזרת התוצאות כטקסט + JSON לשימוש react_visual_agent
        yield _text_event(res["message"])

        return


# instance for easy import in RootAgent
anomaly_agent = AnomalyAgent()
