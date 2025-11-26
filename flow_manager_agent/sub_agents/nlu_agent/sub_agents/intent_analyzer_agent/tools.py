from typing import Any, Dict
from google.adk.tools.tool_context import ToolContext

def exit_pipeline(tool_context: ToolContext) -> Dict[str, Any]:
    tool_context.actions.escalate = True
    return {}