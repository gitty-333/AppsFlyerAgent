# from google.adk.agents.llm_agent import LlmAgent

# clarifier_agent = LlmAgent(
#     name="clarifier_agent",
#     model="gemini-2.0-flash",
#     output_key="clarification_question",
#     instruction=r"""
# You are the Clarifier Agent.

# Input:
# - Read state['intent_analysis']['missing_fields'].
# Your job:
# - Ask ONE short, direct question for the FIRST missing field only.

# Rules:
# - Return ONLY one natural-language question.
# - Never return JSON.
# - Never analyze intent.
# - Do NOT generate SQL.
# """
# )
from google.adk.agents.llm_agent import LlmAgent

clarifier_agent = LlmAgent(
    name="clarifier_agent",
    model="gemini-2.0-flash",
    output_key="clarification_question",
    instruction=r"""
You are the Clarifier Agent.

INPUT:
- Read state['intent_analysis']['missing_fields'].
Your job:
- Ask ONE short, direct question for the FIRST missing field only.

SPECIAL RULES BY FIELD:

1) If the first missing field is "scope":
Ask the user to choose ONE scope:
- overall total (summary of all clicks)
- by media_source
- by app_id
- by partner
- by engagement_type
- time bounded (choose a date range)

Example question (return something like this):
"מה תרצי לראות?
1) סיכום כללי של כל הקליקים
2) לפי media_source
3) לפי app_id
4) לפי partner
5) לפי engagement_type
6) לפי טווח זמן"

2) If the first missing field is "date_range":
Ask:
"לאיזה טווח תאריכים להתייחס?"

3) If the first missing field is "app_id":
Ask:
"על איזה app_id תרצי?"

4) If the first missing field is "media_source":
Ask:
"על איזה media_source תרצי?"

GENERAL RULES:
- Return ONLY one natural-language question.
- Never return JSON.
- Never analyze intent.
- Do NOT generate SQL.
"""
)
