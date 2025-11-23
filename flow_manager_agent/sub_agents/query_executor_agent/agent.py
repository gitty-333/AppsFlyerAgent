from google.adk.agents import Agent
from .bq import BQClient

# יצירת לקוח BigQuery
bq = BQClient()
def run_bigquery(query: str):
    try:
        df = bq.execute_query(query, 'adk_query').to_dataframe()

        return {
            "status": "ok",
            "result": df.to_markdown(index=False),  # needs tabulate
            "message": None,
            "row_count": len(df),
            "executed_sql": query,  # optional, super useful for debugging
        }
    except Exception as e:
        return {
            "status": "error",
            "result": None,
            "message": f"BigQuery error: {e}",
            "executed_sql": query,
        }

# --- האייגנט המתוקן ---
query_executor_agent = Agent(
    name="query_executor_agent",
    model="gemini-2.0-flash",
    description="Executes SQL and returns ONLY tool output.",
instruction="""
You receive the built_query JSON: {built_query}.

If the "status" field in {built_query} is NOT "ok" (e.g., "needs_clarification" or "invalid_fields"), 
your ONLY output MUST be the following JSON:
{"status":"error","result":null,"message":"SQL cannot be executed because status is not ok."}

If the "status" field IS "ok":
1. Extract the 'sql' string from the JSON.
2. Call the run_bigquery tool with the extracted SQL string.
3. Your output MUST be the EXACT, UNMODIFIED result from the tool call.
""",
    tools=[run_bigquery],
    output_key="execution_result",
    generate_content_config={"temperature": 0},
)
