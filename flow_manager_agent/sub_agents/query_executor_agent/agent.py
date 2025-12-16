from google.adk.agents import Agent
from google.adk.agents import LlmAgent
from AppsFlyerAgent.bq import BQClient
import logging
logger = logging.getLogger(__name__) 


def run_bigquery(query: str):
    logger.info("run_bigquery called")          # לוג כללי
    logger.info("SQL to execute:\n%s", query) 
    try:
        
        # 1. יצירת מופע הלקוח בתוך הפונקציה (פתרון הבעיה הגלובלית)
        bq = BQClient() 
        
        # 2. קריאה לפונקציה האמיתית שלך
        # המחלקה BQClient שלך מחזירה RowIterator, שצריך להמיר ל-DataFrame
        result_iterator = bq.execute_query(query, 'adk_query')
        df = result_iterator.to_dataframe()

        return {
            "status": "ok",
            "result": df.to_markdown(index=False), 
            "message": None,
            "row_count": len(df),
            "executed_sql": query,
        }
    except Exception as e:
        logger.exception("BigQuery execution failed") 
        return {
            "status": "error",
            "result": None,
            "message": f"BigQuery execution error: {e}", 
            "executed_sql": query,
        }



query_executor_agent = LlmAgent(
    name="query_executor_agent",
    model="gemini-2.0-flash",
    description="Executes SQL query using the run_bigquery tool.",
    instruction=r"""
You receive a JSON object which is the output of the previous agent.

IMPORTANT:
- Sometimes the previous agent returns:
    { "built_query": {...} }
- And sometimes it returns the built_query directly:
    { "status": "...", "sql": "...", ... }

Your ONLY task is to:
1. If there is a top-level key 'built_query', use that object.
   Otherwise, treat the entire JSON as the built_query object.

2. **CRITICALLY CHECK** the 'status' field inside built_query.
   If it is NOT "ok", return the fixed error JSON:
   {"status":"error","result":null,"message":"SQL cannot be executed because status is not ok."}

3. If the status IS "ok", extract the 'sql' string from built_query.

4. **IMMEDIATELY** call the run_bigquery tool with the extracted SQL string as the 'query' argument.

5. Your final output MUST be the EXACT result of the tool call.
""",
    tools=[run_bigquery],
    output_key="execution_result",
    generate_content_config={"temperature": 0},
)
