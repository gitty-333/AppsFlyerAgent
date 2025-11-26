from google.adk.agents import Agent
from .bq import BQClient # שינוי זה לשם המודול שבו נמצא BQClient

# יצירת לקוח BigQuery - זוהי הנחת עבודה
# ודא שמחלקה BQClient המקורית (שלא מכילה Mocking) זמינה לייבוא
from .bq import BQClient 

def run_bigquery(query: str):
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
        return {
            "status": "error",
            "result": None,
            "message": f"BigQuery execution error: {e}", 
            "executed_sql": query,
        }
# --- האייגנט המתוקן והמחייב ---
query_executor_agent = Agent(
    name="query_executor_agent",
    model="gemini-2.0-flash",
    description="Executes SQL query using the run_bigquery tool.",
    instruction="""
You receive a JSON object which is the output of the previous agent.
This output CONTAINS the result of the SQL builder under the key 'built_query'.

Your ONLY task is to:
1. **Locate** the 'built_query' object.
2. **CRITICALLY CHECK** the 'status' field within 'built_query'. If it is NOT "ok", return the fixed error JSON: 
   {"status":"error","result":null,"message":"SQL cannot be executed because status is not ok."}

3. **EXECUTE:** If the status IS "ok", extract the 'sql' string from 'built_query'.
4. **IMMEDIATELY** call the run_bigquery tool with the extracted SQL string as the 'query' argument.
5. Your final output MUST be the EXACT result of the tool call.
""",
    tools=[run_bigquery],
    output_key="execution_result",
    generate_content_config={"temperature": 0}, 
)

