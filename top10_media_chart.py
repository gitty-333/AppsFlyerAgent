import pandas as pd
import matplotlib.pyplot as plt

from bq import BQClient


# השאילתה - בדיוק כמו שכתבת
ALL_MEDIA_SQL = """
SELECT
    DATE(event_time) AS event_date,
    hr AS event_hour,
    media_source,
    SUM(total_events) AS total_clicks
FROM `practicode-2025.clicks_data_prac.partial_encoded_clicks_part`
WHERE media_source = 'media_source_1032'
GROUP BY
    event_date,
    event_hour,
    media_source
ORDER BY
    media_source;
"""


def main():
    client = BQClient()

    # מריצים את השאילתה ומקבלים DataFrame
    df = client.execute_query(ALL_MEDIA_SQL, "all_media_by_hour").to_dataframe()

    if df.empty:
        print("לא חזרו נתונים מהשאילתה.")
        return

    # בונים timestamp מלא מתאריך + שעה
    # event_date = עמודה של תאריך
    # event_hour = int בין 0 ל-23
    df["event_ts"] = pd.to_datetime(df["event_date"].astype(str)) + pd.to_timedelta(
        df["event_hour"], unit="h"
    )

    # מיון לפי זמן
    df = df.sort_values("event_ts")

    # נסכום סה"כ קליקים לכל media_source
    totals = (
        df.groupby("media_source")["total_clicks"]
        .sum()
        .sort_values(ascending=False)
    )

    # נבחר TOP N כדי שהגרף יהיה קריא
    TOP_N = 10
    top_sources = totals.head(TOP_N).index.tolist()

    print(f"משרטטת את TOP {TOP_N} media_source-ים:")
    for src in top_sources:
        print("  -", src)

    df_top = df[df["media_source"].isin(top_sources)]

    # pivot: שורה = זמן, עמודות = media_source, ערך = total_clicks
    pivot = (
        df_top.pivot(
            index="event_ts",
            columns="media_source",
            values="total_clicks",
        )
        .fillna(0)
        .sort_index()
    )

    # גרף
    plt.style.use("dark_background")
    plt.figure(figsize=(12, 6))

    for media in pivot.columns:
        plt.plot(
            pivot.index,
            pivot[media],
            linewidth=2,
            alpha=0.8,
            label=media,
        )

    plt.title("Hourly Clicks per Media Source (TOP 10)")
    plt.xlabel("Time")
    plt.ylabel("Total Clicks")
    plt.xticks(rotation=45)

    # legend קטן יחסית
    plt.legend(fontsize=8, ncol=2)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
