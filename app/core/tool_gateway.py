import logging
from typing import Dict, Any
from app.mcp.razorpay_client import _call_mcp_tool

logger = logging.getLogger(__name__)

def has_permission(agent_name: str, tool_name: str) -> bool:
    """Basic RBAC check for tool access."""
    # Add proper role-based access control rules here.
    # For now, allow everything if the agent is known.
    allowed_agents = ["payment_orchestrator", "transaction_verifier", "recovery_service", "intent_agent"]
    return agent_name in allowed_agents

def execute_tool_call(agent_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
    """
    Central gateway for executing specialized tools (MCP or local).
    Enforces permissions and provides a single integration point.
    """
    if not has_permission(agent_name, tool_name):
        raise PermissionError(f"Agent '{agent_name}' lacks permission to execute tool '{tool_name}'")

    if tool_name.startswith("razorpay_"):
        from app.mcp import razorpay_client
        mcp_tool = tool_name.replace("razorpay_", "")
        
        if mcp_tool == "create_order":
            return razorpay_client.create_order(**arguments)
        elif mcp_tool == "fetch_order":
            return razorpay_client.fetch_payment_status(**arguments)
        elif mcp_tool == "capture_payment":
            return razorpay_client.capture_payment(**arguments)
        elif mcp_tool == "refund_payment":
            return razorpay_client.refund_payment(**arguments)
        
        return razorpay_client._call_mcp_tool(mcp_tool, arguments)
    
    raise ValueError(f"Unknown tool '{tool_name}' requested by '{agent_name}'")
