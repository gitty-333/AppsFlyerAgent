from typing import AsyncGenerator
from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.genai import types
from pathlib import Path
import logging

from ....bq import BQClient  # התאימי אם הנתיב שונה אצלך

logger = logging.getLogger(__name__)

def _text_event(msg: str) -> Event:
    return Event(
        author="assistant",
        content=types.Content(parts=[types.Part(text=msg)])
    )

# --- SQL loading ---
BASE_DIR = Path(__file__).parent
SPIKE_SQL = (BASE_DIR / "queries" / "spike_clicks.sql").read_text(encoding="utf-8")
DROP_SQL  = (BASE_DIR / "queries" / "drop_clicks.sql").read_text(encoding="utf-8")


class AnomalyAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="anomaly_agent")
        self.client = BQClient()

    def pull_data(self):
        spike_df = self.client.execute_query(SPIKE_SQL, "anomaly_spike").to_dataframe()
        drop_df  = self.client.execute_query(DROP_SQL,  "anomaly_drop").to_dataframe()
        return {"spike": spike_df, "drop": drop_df}

    def detect_anomalies(self, results):
        anomalies = {}
        if not results["spike"].empty:
            anomalies["click_spike"] = results["spike"]
        if not results["drop"].empty:
            anomalies["click_drop"] = results["drop"]
        return anomalies

    def report(self, anomalies):
        if not anomalies:
            return {"status": "ok", "message": "לא נמצאו אנומליות.", "anomalies": {}}

        parts = [f"{k}: נמצאו {len(df)} חריגות" for k, df in anomalies.items()]
        return {"status": "ok", "message": " | ".join(parts), "anomalies": anomalies}

    async def _run_async_impl(self, context) -> AsyncGenerator[Event, None]:
        state = context.session.state

        data = self.pull_data()
        anomalies = self.detect_anomalies(data)
        res = self.report(anomalies)

        state["anomaly_result"] = res
        yield _text_event(res["message"])
        return


anomaly_agent = AnomalyAgent()