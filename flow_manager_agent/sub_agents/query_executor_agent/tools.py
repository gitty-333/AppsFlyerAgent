from .bq import BQClient

def run_bigquery(query: str):
    """
    Executes a SQL query in BigQuery and returns a markdown table.
    """
    try:
        bq = BQClient()
        result_iterator = bq.execute_query(query, "adk_query")
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
