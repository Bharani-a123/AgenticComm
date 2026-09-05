from langgraph.graph import StateGraph, END
from app.agents.state import ConversationState
from app.agents.agent_intent import run_intent_agent
from app.agents.agent_clarify import run_clarify_agent
from app.agents.agent_discovery import run_discovery_agent
from app.agents.agent_ranking import run_ranking_agent

def route_after_intent(state: ConversationState):
    if state.get("unsupported_category"):
        return END
    if state.get("intent_mandate") is not None:
        return "discovery_agent"
    return "clarify_agent"
    
def route_after_clarify(state: ConversationState):
    if state.get("intent_mandate") is not None:
        return "discovery_agent"
    return END

workflow = StateGraph(ConversationState)
workflow.add_node("intent_agent", run_intent_agent)
workflow.add_node("clarify_agent", run_clarify_agent)
workflow.add_node("discovery_agent", run_discovery_agent)
workflow.add_node("ranking_agent", run_ranking_agent)

workflow.set_entry_point("intent_agent")
workflow.add_conditional_edges("intent_agent", route_after_intent)
workflow.add_conditional_edges("clarify_agent", route_after_clarify)
workflow.add_edge("discovery_agent", "ranking_agent")
workflow.add_edge("ranking_agent", END)

app_graph = workflow.compile()

def run_conversation_turn(state: ConversationState, new_user_message: str | None) -> ConversationState:
    if new_user_message:
        state["raw_query"] = new_user_message
        if "messages" not in state: state["messages"] = []
        state["messages"].append({"role": "user", "content": new_user_message})
        
    new_state = app_graph.invoke(state)
    return new_state
