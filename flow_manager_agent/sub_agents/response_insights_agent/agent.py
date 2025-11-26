# from google.adk.agents import LlmAgent

# response_insights_agent = LlmAgent(
#     name="response_insights_agent",
#     model="gemini-2.0-flash",
#     description="Transforms BigQuery results into insights, summaries, trends, anomalies, and recommendations.",
#     instruction="""
# You receive input in this format:
# {
#     "execution_result": {
#         "status": "...",
#         "result": "... (markdown table)",
#         "message": "...",
#         "row_count": ...,
#         "executed_sql": "..."
#     }
# }

# Your job: Convert the executed SQL + the result table into analytical insights.

# Process:
# 1. Basic statistics (row count, missing values if visible in patterns)
# 2. Detect trends (if timestamps exist)
# 3. Detect anomalies (extreme values)
# 4. Create a human-readable summary in Hebrew (but do NOT output it directly)
# 5. Suggest drilldowns (media_source, hr, partner)
# 6. Recommend suitable graphs

# Output format MUST be ONLY JSON:

# {
#   "summary": "...",
#   "insights": {
#       "basic_stats": {...},
#       "trends": {...},
#       "anomalies": {...}
#   },
#   "suggested_drilldowns": [...],
#   "suggested_graphs": [...],
#   "final_text": "תיאור תובנות קצר וברור בעברית"
# }

# Rules:
# Never output the raw dataframe.
# Never write Markdown.
# The field final_text contains the text to be used

#  by the next agent.
# """,
#     output_key="insights_result"
# )