# from google.adk.agents import LlmAgent

# human_response_agent = LlmAgent(
#     name="human_response_agent",
#     model="gemini-2.0-flash",
#     description="Converts analytical insights into a final user-facing response in Hebrew.",
#     instruction="""
# You receive data from response_insights_agent in this format:
# {
#    "insights_result": {
#        "summary": "...",
#        "insights": {...},
#        "suggested_drilldowns": [...],
#        "suggested_graphs": [...],
#        "final_text": "..."
#    }
# }

# Your task:
# Turn the insights JSON into a clean, friendly response for the end user in Hebrew.

# Output rules:
# Output clean Hebrew text only.
# No JSON.
# No English unless part of a field name.
# Be short, structured, and readable.
# Include:
#    • Summary
#    • Key findings
#    • If relevant: What the user can check next (drilldowns)
# """,
#     output_key=None
# )