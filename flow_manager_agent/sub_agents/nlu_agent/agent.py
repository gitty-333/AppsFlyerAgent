from google.adk.agents import SequentialAgent
from .sub_agents.intent_analyzer_agent.agent import intent_analyzer_agent

nlu_agent = SequentialAgent(
    name="nlu_agent",
    sub_agents=[intent_analyzer_agent],
    description="NLU frontdoor: intent analysis only."
)
