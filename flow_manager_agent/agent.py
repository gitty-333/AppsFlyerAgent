from typing import AsyncGenerator
from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.genai import types

from .utils.json_utils import clean_json as _clean_json

# --- Sub Agents ---
from .sub_agents.intent_analyzer_agent import intent_analyzer_agent
from .sub_agents.clarifier_orchestrator_agent import clarifier_agent
from .sub_agents.protected_query_builder_agent import protected_query_builder_agent
from .sub_agents.query_executor_agent import query_executor_agent
from .sub_agents.response_insights_agent import response_insights_agent
from .sub_agents.human_response_agent import human_response_agent

import json
import re
import logging


def _text_event(message: str) -> Event:
    """Helper: convert plain text into ADK Event."""
    return Event(
        author="assistant",
        content=types.Content(parts=[types.Part(text=message)])
    )


class RootAgent(BaseAgent):
    """Single orchestrator for the entire system."""

    def __init__(self):
        super().__init__(name="root_agent")

    async def _run_async_impl(self, context) -> AsyncGenerator[Event, None]:
        session_state = context.session.state

        # ============================================================
        # 1) INTENT ANALYZER
        # ============================================================
        logging.info("[RootAgent] === STEP 1: intent_analyzer_agent START ===")
        async for event in intent_analyzer_agent.run_async(context):
            yield event
        logging.info("[RootAgent] === STEP 1: intent_analyzer_agent END ===")

        intent_analysis = _clean_json(session_state.get("intent_analysis"))
        logging.info(f"[RootAgent] intent_analysis raw: {intent_analysis}")

        status = intent_analysis.get("status")
        if status == "not relevant":  # normalization
            status = "not_relevant"

        logging.info(f"[RootAgent] intent_analysis status: {status}")

        # ============================================================
        # 2) CLARIFICATION FLOW (from NLU)
        # ============================================================
        if status == "clarification_needed":
            missing_fields = intent_analysis.get("missing_fields", [])
            session_state["missing_fields"] = missing_fields

            logging.info(f"[RootAgent] clarification_needed missing_fields: {missing_fields}")
            logging.info("[RootAgent] === STEP 2: clarifier_agent START ===")
            async for event in clarifier_agent.run_async(context):
                yield event
            logging.info("[RootAgent] === STEP 2: clarifier_agent END ===")

            return   # STOP → wait for next user message

        # ============================================================
        # 3) STOP ON ERROR / NOT RELEVANT (from NLU)
        # ============================================================
        if status in ("not_relevant", "error"):
            user_message = intent_analysis.get("message", "Request not supported.")
            logging.info(f"[RootAgent] stopping early. message: {user_message}")
            yield _text_event(user_message)
            return

        # ============================================================
        # 4) OK → START FULL PIPELINE
        # ============================================================
        if status == "ok":

            # ---------------------------
            # STEP A: SQL BUILDER
            # ---------------------------
            logging.info("[RootAgent] === STEP A: protected_query_builder_agent START ===")
            async for event in protected_query_builder_agent.run_async(context):
                yield event
            logging.info("[RootAgent] === STEP A: protected_query_builder_agent END ===")

            built_query_raw = session_state.get("built_query")
            logging.info(f"[RootAgent] raw built_query: {built_query_raw}")

            cleaned_built_query = self._parse_built_query(built_query_raw)
            logging.info(f"[RootAgent] parsed built_query: {cleaned_built_query}")

            if cleaned_built_query is None:
                logging.error("[RootAgent] Builder returned invalid JSON.")
                yield _text_event("SQL Builder returned invalid JSON.")
                return

            builder_status = cleaned_built_query.get("status")
            logging.info(f"[RootAgent] builder status: {builder_status}")

            # ✅ NEW: handle builder clarification
            if builder_status == "needs_clarification":
                questions = cleaned_built_query.get("clarification_questions", [])
                msg = cleaned_built_query.get("message", "")

                logging.info(f"[RootAgent] Builder needs clarification: {questions}")

                # אם יש message נחזיר אותו, אחרת את השאלות
                if msg:
                    yield _text_event(msg)
                if questions:
                    yield _text_event("\n".join(questions))

                return

            # ✅ NEW: handle invalid_fields / error from builder
            if builder_status != "ok":
                msg = cleaned_built_query.get("message", "SQL Builder returned an error.")
                invalid_fields = cleaned_built_query.get("invalid_fields", [])

                logging.info(f"[RootAgent] Builder failed. message={msg} invalid_fields={invalid_fields}")

                if invalid_fields:
                    yield _text_event(
                        f"{msg}\nInvalid fields: {', '.join(invalid_fields)}"
                    )
                else:
                    yield _text_event(msg)

                return

            # ---------------------------
            # STEP B: SQL EXECUTOR
            # ---------------------------
            BLUE = "\033[94m"
            GREEN = "\033[92m"
            RESET = "\033[0m"

            print(f"{BLUE}=== BEFORE BigQuery EXECUTION ==={RESET}")
            logging.info("=== BEFORE BigQuery EXECUTION ===")

            async for event in query_executor_agent.run_async(context):
                yield event

            print(f"{GREEN}=== AFTER BigQuery EXECUTION ==={RESET}")
            logging.info("=== AFTER BigQuery EXECUTION ===")

            sql_execution_result = _clean_json(session_state.get("execution_result", {}))
            logging.info(f"[RootAgent] execution_result: {sql_execution_result}")

            # ---------------------------
            # STEP C: INSIGHTS AGENT
            # ---------------------------
            session_state["insights_payload"] = {
                "execution_result": sql_execution_result
            }

            logging.info("[RootAgent] === STEP C: response_insights_agent START ===")
            async for event in response_insights_agent.run_async(context):
                yield event
            logging.info("[RootAgent] === STEP C: response_insights_agent END ===")

            # ---------------------------
            # STEP D: HUMAN RESPONSE
            # ---------------------------
            logging.info("[RootAgent] === STEP D: human_response_agent START ===")
            async for event in human_response_agent.run_async(context):
                yield event
            logging.info("[RootAgent] === STEP D: human_response_agent END ===")

            return

        # ============================================================
        # 5) FALLBACK
        # ============================================================
        logging.warning("[RootAgent] fallback reached.")
        yield _text_event("I couldn't understand the request.")
        return

    # ====================================================================
    # Helper: Clean/Parse built_query JSON
    # ====================================================================
    def _parse_built_query(self, raw):
        """Convert raw built_query into dict safely."""
        if isinstance(raw, dict):
            return raw

        if isinstance(raw, str):
            cleaned = raw.strip()
            cleaned = re.sub(r"```json|```", "", cleaned).strip()

            try:
                return json.loads(cleaned)
            except Exception:
                logging.error("[RootAgent] Failed to parse built_query JSON.")
                return None

        logging.error("[RootAgent] built_query is neither dict nor string.")
        return None


# Create the actual agent instance
root_agent = RootAgent()
