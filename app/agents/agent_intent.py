import json
import os
import uuid
from app.agents.state import ConversationState
from app.agents.llm_client import call_llm
from app.taxonomy.schema_matcher import compute_delta
from app.protocols.ap2.mandates import IntentMandate
from app.services.audit_ledger import write_audit_log
from app.db.postgres import SessionLocal

def get_schema(category: str):
    path = f"app/taxonomy/schemas/{category}.json"
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {"required_attributes": {}}


def get_all_schemas_summary() -> str:
    """
    Loads every category schema and builds a compact reference the LLM can use
    to pick the RIGHT field names on the very first message -- before we even
    know which category the user meant. This fixes the bug where turn-1
    extraction invents its own key names (e.g. 'budget' instead of 'budget_max'),
    which then never satisfies compute_delta's exact-key check.
    """
    categories = ["saree", "mesh_chair", "running_shoes", "smartphone", "backpack"]
    summary = {}
    for cat in categories:
        schema = get_schema(cat)
        summary[cat] = schema.get("required_attributes", {})
    return json.dumps(summary)

def run_intent_agent(state: ConversationState) -> ConversationState:
    # Clear previous candidates to avoid displaying old products when asking for clarifications
    if state.get("raw_query"):
        state["candidate_products"] = []
        state["intent_mandate"] = None

    category = state.get("category")

    # Always give the LLM the full canonical field-name reference, even before
    # we know the category -- this is what lets turn-1 extraction use the
    # RIGHT key names (e.g. budget_max, not budget) instead of guessing.
    taxonomy_summary = get_all_schemas_summary()
    schema_hint = f"\nCanonical field names per category (use these EXACT keys in constraints): {taxonomy_summary}"
    if category:
        schema = get_schema(category)
        schema_hint += f"\nUser's category is already known to be '{category}'. Its exact schema: {json.dumps(schema)}"
        
    with open("app/agents/prompts/intent.md") as f:
        prompt = f.read() + schema_hint
    
    # Send the last few messages for context
    messages = state.get("messages", [])
    if messages:
        context = "\n".join([f"{m['role']}: {m['content']}" for m in messages[-3:]])
    else:
        context = state.get("raw_query", "")
        
    try:
        resp_str = call_llm(prompt, context, json_mode=True)
        resp = json.loads(resp_str)
    except (json.JSONDecodeError, Exception) as e:
        state["unsupported_category"] = False
        if "messages" not in state: state["messages"] = []
        state["messages"].append({"role": "assistant", "content": "Sorry, I had trouble understanding that. Could you rephrase?"})
        return state
    
    category = resp.get("category")
    valid_categories = ["saree", "mesh_chair", "running_shoes", "smartphone", "backpack"]
    
    if category not in valid_categories:
        state["unsupported_category"] = True
        state["category"] = None
        if "messages" not in state: state["messages"] = []
        state["messages"].append({"role": "assistant", "content": "Category not supported."})
        return state
        
    if state.get("category") and category != state.get("category"):
        state["constraints"] = {}
        
    state["category"] = category
    state["unsupported_category"] = False
    
    if state.get("constraints") is None:
        state["constraints"] = {}
    
    constraints_raw = resp.get("constraints") or {}
    if not isinstance(constraints_raw, dict):
        constraints_raw = {}
        
    for k, v in constraints_raw.items():

        if k not in state["constraints"] or state["constraints"][k] is None:
            state["constraints"][k] = v
            
    schema = get_schema(category)
    missing = compute_delta(state["constraints"], schema)
    state["missing_fields"] = missing
    
    # Extract options for missing fields from schema
    options = {}
    if schema and "required_attributes" in schema:
        for m in missing:
            if m in schema["required_attributes"]:
                options[m] = schema["required_attributes"][m]
    state["missing_field_options"] = options
    
    if not missing:
        final_constraints = dict(state["constraints"])
        if state.get("user_mandate_limit"):
            final_constraints["user_mandate_limit"] = state.get("user_mandate_limit")
            
        state["intent_mandate"] = IntentMandate(
            mandate_id=uuid.uuid4(),
            user_id=state.get("user_id") or "default_user",
            category=category,
            constraints=final_constraints,
            autopay_limit=state.get("user_autopay_limit") if state.get("user_autopay_limit") is not None else 0.0,
            completeness=1.0
        )
        db = SessionLocal()
        try:
            write_audit_log(db, "intent_agent", "intent_complete", state["intent_mandate"].mandate_id, None, state["constraints"], "Intent complete")
        finally:
            db.close()
            
    return state
