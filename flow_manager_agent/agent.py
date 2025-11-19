# """תאור"""

from google.adk.agents import SequentialAgent

from .sub_agents.nlu_agent import nlu_agent
from .sub_agents.protected_query_builder_agent import protected_query_builder_agent
from .sub_agents.query_executor_agent import query_executor_agent

from dotenv import load_dotenv
load_dotenv()

root_agent = SequentialAgent(
    name="flow_manager_agent",
    sub_agents=[
        nlu_agent,
        protected_query_builder_agent,
        query_executor_agent

    ],
    description="A pipeline that parses user queries and converts them into SQL queries, passes the queries to BigQuery execution, and returns validated, anomaly-aware, and user-friendly answers."
)