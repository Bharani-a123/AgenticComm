import uuid
from app.agents.state import ConversationState
from app.agents.llm_client import call_llm
from app.protocols.ap2.mandates import IntentMandate
from app.services.audit_ledger import write_audit_log
from app.db.postgres import SessionLocal

def run_clarify_agent(state: ConversationState) -> ConversationState:
    clarify_round = state.get("clarify_round")
    if clarify_round is None:
        clarify_round = 0
    
    if clarify_round >= 3:
        # HARD CAP
        for mf in state.get("missing_fields", []):
            if "budget" in mf:
                state["constraints"][mf] = 2000.0
            else:
                state["constraints"][mf] = "any"
                
        state["intent_mandate"] = IntentMandate(
            mandate_id=uuid.uuid4(),
            user_id=state.get("user_id") or "default_user",
            category=state.get("category"),
            constraints=state["constraints"],
            autopay_limit=state["constraints"].get("budget_max", 1000.0),
            completeness=0.5
        )
        
        db = SessionLocal()
        try:
            write_audit_log(db, "clarify_agent", "intent_capped", state["intent_mandate"].mandate_id, None, state["constraints"], "Clarify loop capped at 3 rounds")
        finally:
            db.close()
            
        return state

    with open("app/agents/prompts/clarify.md") as f:
        prompt = f.read()

    missing_options = state.get("missing_field_options", {})
    category = state.get("category", "item")
    user_context = f"category={category}, missing={missing_options}"

    q = call_llm(prompt, user_context)
    if "messages" not in state: state["messages"] = []
    state["messages"].append({"role": "assistant", "content": q})
    state["clarify_round"] = clarify_round + 1
    return state
