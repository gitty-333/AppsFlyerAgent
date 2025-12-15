from typing import AsyncGenerator
from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.genai import types

from .utils.json_utils import clean_json as _clean_json

# --- Sub Agents ---
from .sub_agents.intent_analyzer_agent import intent_analyzer_agent, BASE_NLU_SPEC
from .sub_agents.anomaly_agent import anomaly_agent   # ✅ NEW IMPORT
from .sub_agents.react_visual_agent import react_visual_agent
from .sub_agents.clarifier_orchestrator_agent import clarifier_agent
from .sub_agents.protected_query_builder_agent import protected_query_builder_agent
from .sub_agents.query_executor_agent import query_executor_agent
from .sub_agents.response_insights_agent import response_insights_agent
from .sub_agents.human_response_agent import human_response_agent

import json
import re
import logging
from datetime import datetime, timedelta
import pytz


def _text_event(message: str) -> Event:
    return Event(
        author="assistant",
        content=types.Content(parts=[types.Part(text=message)])
    )


class RootAgent(BaseAgent):

    def __init__(self):
        super().__init__(name="root_agent")

    async def _run_async_impl(self, context) -> AsyncGenerator[Event, None]:

        session_state = context.session.state

        # ============================================================
        # STEP 0 — Inject current date into NLU instruction
        # ============================================================
        tz = pytz.timezone("Asia/Jerusalem")
        today = datetime.now(tz).date()
        yesterday = today - timedelta(days=1)
        day_before = today - timedelta(days=2)

        dynamic_date_block = f"""
            # SYSTEM DATE DIRECTIVE — DO NOT IGNORE
            Current real date: {today.strftime("%Y-%m-%d")}

            Natural-language date mapping:
            - "today" / "היום" → {today}
            - "yesterday" / "אתמול" → {yesterday}
            - "שלשום" → {day_before}

            Dates without year (24.10, 25/10, 25.10):
            → ALWAYS use year {today.year}.

            If interpreted date is in the future → return future-date error.

            # END OF DATE DIRECTIVE
        """

        intent_analyzer_agent.instruction = dynamic_date_block + BASE_NLU_SPEC

        # ============================================================
        # STEP 1 — Intent Analyzer
        # ============================================================
        async for event in intent_analyzer_agent.run_async(context):
            yield event

        intent_analysis = _clean_json(session_state.get("intent_analysis"))
        status = intent_analysis.get("status")

        if status == "not relevant":
            status = "not_relevant"

        # ============================================================
        # STEP 2 — Clarification needed
        # ============================================================
        if status == "clarification_needed":
            session_state["missing_fields"] = intent_analysis.get("missing_fields", [])

            async for event in clarifier_agent.run_async(context):
                yield event

            return

        # ============================================================
        # STEP 3 — Hard stop (error / not relevant)
        # ============================================================
        if status in ("not_relevant", "error"):
            yield _text_event(intent_analysis.get("message", "Request not supported."))
            return

        # ============================================================
        # STEP 4 — OK → run pipeline
        # ============================================================
        if status == "ok":
            parsed_intent = intent_analysis.get("parsed_intent", {})
            intent_type = parsed_intent.get("intent")

            # ---------------------------
            # ✅ ANOMALY FLOW (NEW)
            # ---------------------------
            if intent_type == "anomaly":
                # מריץ BigQuery + מזהה אנומליות
                logging.info("[RootAgent] === ANOMALY FLOW START ===")
                async for event in anomaly_agent.run_async(context):
                    yield event
                # מריץ ויזואליזציה (קורא anomaly_result מה-state)
                async for event in react_visual_agent.run_async(context):
                    yield event
                logging.info("[RootAgent] === ANOMALY FLOW END ===")
                return  # ✅ stop here, dont continue to SQL builder

            # ---------------------------
            # Normal analytics / retrieval flow
            # ---------------------------

            # SQL Builder
            async for event in protected_query_builder_agent.run_async(context):
                yield event

            built_query_raw = session_state.get("built_query")
            built_query = self._parse_built_query(built_query_raw)

            if built_query.get("status") != "ok":
                yield _text_event(built_query.get("message", "SQL Builder error"))
                return

            # Query Executor
            async for event in query_executor_agent.run_async(context):
                yield event

            sql_result = _clean_json(session_state.get("execution_result", {}))

            # Insights Agent
            session_state["insights_payload"] = {"execution_result": sql_result}
            async for event in response_insights_agent.run_async(context):
                yield event

            # Human Response Agent
            async for event in human_response_agent.run_async(context):
                yield event

            return

        # fallback (shouldn't reach)
        yield _text_event("I couldn't understand the request.")
        return


    # ===== JSON Parse Helper =====
    def _parse_built_query(self, raw):
        if isinstance(raw, dict):
            return raw

        if isinstance(raw, str):
            cleaned = re.sub(r"```json|```", "", raw.strip())
            try:
                return json.loads(cleaned)
            except:
                return {"status": "error", "message": "Invalid JSON from builder"}

        return {"status": "error", "message": "Invalid builder output"}


root_agent = RootAgent()
