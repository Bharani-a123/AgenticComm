import os

files = {
    "app/taxonomy/schema_matcher.py": '''\
def compute_delta(user_constraints: dict, schema: dict) -> list[str]:
    """Pure function. Returns list of required_attributes keys from schema that are
    missing or None in user_constraints. No LLM, no I/O. O(1)-ish, just dict diffing."""
    required = schema.get("required_attributes", [])
    missing = []
    for req in required:
        if req not in user_constraints or user_constraints[req] is None:
            missing.append(req)
    return missing
''',
    "app/agents/state.py": '''\
from typing import TypedDict, Optional, List, Dict, Any
from uuid import UUID
from app.protocols.ap2.mandates import IntentMandate, CartMandate

class ConversationState(TypedDict):
    user_id: str
    raw_query: str
    category: Optional[str]
    constraints: Dict[str, Any]
    clarify_round: int
    intent_mandate: Optional[IntentMandate]
    candidate_products: List[Dict[str, Any]]
    selected_product_id: Optional[UUID]
    cart_mandate: Optional[CartMandate]
    messages: List[Dict[str, Any]]
    missing_fields: List[str]
    unsupported_category: bool
''',
    "app/agents/llm_client.py": '''\
def call_llm(system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
    """Stub for Anthropic API. Mocked in tests."""
    raise NotImplementedError("LLM not wired.")
''',
    "app/agents/prompts/intent.md": '''\
Extract category and constraints. Known categories: saree, mesh_chair, running_shoes, smartphone, backpack.
Return STRICT JSON.
''',
    "app/agents/prompts/clarify.md": '''\
Generate ONE short question asking for all missing fields.
''',
    "app/agents/prompts/discovery.md": '''\
Discovery prompt.
''',
    "app/agents/prompts/ranking.md": '''\
Rank products with a 1-sentence explanation. Return STRICT JSON list.
''',
    "app/agents/agent_intent.py": '''\
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
    return {"required_attributes": []}

def run_intent_agent(state: ConversationState) -> ConversationState:
    with open("app/agents/prompts/intent.md") as f:
        prompt = f.read()
    
    resp_str = call_llm(prompt, state.get("raw_query", ""), json_mode=True)
    resp = json.loads(resp_str)
    
    category = resp.get("category")
    if category not in ["saree", "mesh_chair", "running_shoes", "smartphone", "backpack"]:
        state["unsupported_category"] = True
        state["category"] = None
        if "messages" not in state: state["messages"] = []
        state["messages"].append({"role": "assistant", "content": "Category not supported."})
        return state
        
    state["category"] = category
    state["unsupported_category"] = False
    
    if "constraints" not in state: state["constraints"] = {}
    for k, v in resp.get("constraints", {}).items():
        if k not in state["constraints"] or state["constraints"][k] is None:
            state["constraints"][k] = v
            
    schema = get_schema(category)
    missing = compute_delta(state["constraints"], schema)
    state["missing_fields"] = missing
    
    if not missing:
        state["intent_mandate"] = IntentMandate(
            mandate_id=uuid.uuid4(),
            user_id=state.get("user_id", "default_user"),
            category=category,
            constraints=state["constraints"],
            autopay_limit=state["constraints"].get("budget_max", 1000.0),
            completeness=1.0
        )
        db = SessionLocal()
        try:
            write_audit_log(db, "intent_agent", "intent_complete", state["intent_mandate"].mandate_id, None, state["constraints"], "Intent complete")
        finally:
            db.close()
            
    return state
''',
    "app/agents/agent_clarify.py": '''\
import uuid
from app.agents.state import ConversationState
from app.agents.llm_client import call_llm
from app.protocols.ap2.mandates import IntentMandate
from app.services.audit_ledger import write_audit_log
from app.db.postgres import SessionLocal

def run_clarify_agent(state: ConversationState) -> ConversationState:
    clarify_round = state.get("clarify_round", 0)
    
    if clarify_round >= 3:
        # HARD CAP
        for mf in state.get("missing_fields", []):
            if "budget" in mf:
                state["constraints"][mf] = 2000.0
            else:
                state["constraints"][mf] = "any"
                
        state["intent_mandate"] = IntentMandate(
            mandate_id=uuid.uuid4(),
            user_id=state.get("user_id", "default_user"),
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
        
    q = call_llm(prompt, str(state.get("missing_fields", [])))
    if "messages" not in state: state["messages"] = []
    state["messages"].append({"role": "assistant", "content": q})
    state["clarify_round"] = clarify_round + 1
    return state
''',
    "app/agents/agent_discovery.py": '''\
from app.agents.state import ConversationState
from app.db.postgres import SessionLocal
from app.db.models import Product
from app.services.ranking_pre_filter import pre_filter_products

def run_discovery_agent(state: ConversationState) -> ConversationState:
    if not state.get("intent_mandate"):
        return state
        
    db = SessionLocal()
    try:
        # 1. Query Postgres for products simulating parallel ACP calls
        db_products = db.query(Product).filter(Product.category == state["intent_mandate"].category).all()
        
        # Convert to dicts using normalized if available, else raw
        raw_list = []
        for p in db_products:
            d = p.normalized if p.normalized else p.raw_attributes
            d["id"] = str(p.product_id)
            d["category"] = p.category
            raw_list.append(d)
            
        # 2. Pre-filter BEFORE LLM
        filtered = pre_filter_products(raw_list, state["intent_mandate"])
        
        if not filtered:
            state["candidate_products"] = []
            if "messages" not in state: state["messages"] = []
            state["messages"].append({"role": "assistant", "content": "No matches found."})
        else:
            state["candidate_products"] = filtered
            
    finally:
        db.close()
        
    return state
''',
    "app/agents/agent_ranking.py": '''\
import json
from app.agents.state import ConversationState
from app.agents.llm_client import call_llm
from app.services.audit_ledger import write_audit_log
from app.db.postgres import SessionLocal

def run_ranking_agent(state: ConversationState) -> ConversationState:
    candidates = state.get("candidate_products", [])
    if not candidates:
        return state
        
    with open("app/agents/prompts/ranking.md") as f:
        prompt = f.read()
        
    resp_str = call_llm(prompt, json.dumps(candidates), json_mode=True)
    try:
        ranked_items = json.loads(resp_str)
    except:
        ranked_items = []
        
    valid_ids = {str(c["id"]) for c in candidates}
    
    final_list = []
    for item in ranked_items:
        pid = str(item.get("product_id"))
        if pid in valid_ids:
            # Find original
            orig = next(c for c in candidates if str(c["id"]) == pid)
            orig["rank"] = item.get("rank")
            orig["explanation"] = item.get("explanation")
            final_list.append(orig)
            
    # Sort by rank
    final_list.sort(key=lambda x: x.get("rank", 999))
    state["candidate_products"] = final_list
    
    db = SessionLocal()
    try:
        write_audit_log(db, "ranking_agent", "ranked", None, None, None, "Ranked candidates")
    finally:
        db.close()
        
    return state
''',
    "app/agents/graph.py": '''\
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
''',
    "tests/test_intent_agent.py": '''\
import pytest
from unittest.mock import patch
from app.agents.state import ConversationState
from app.agents.agent_intent import run_intent_agent

@patch("app.agents.agent_intent.call_llm")
def test_intent_agent_complete(mock_call):
    mock_call.return_value = '{"category": "saree", "constraints": {"fabric": "silk", "color": "red"}}'
    state = ConversationState(raw_query="i want a red silk saree", constraints={}, messages=[])
    
    with patch("app.agents.agent_intent.get_schema") as mock_schema:
        mock_schema.return_value = {"required_attributes": ["fabric", "color"]}
        res = run_intent_agent(state)
        
        assert res["intent_mandate"] is not None
        assert res["intent_mandate"].category == "saree"
        assert not res.get("unsupported_category")

@patch("app.agents.agent_intent.call_llm")
def test_intent_agent_partial(mock_call):
    mock_call.return_value = '{"category": "saree", "constraints": {"color": "red"}}'
    state = ConversationState(raw_query="i want a red saree", constraints={}, messages=[])
    
    with patch("app.agents.agent_intent.get_schema") as mock_schema:
        mock_schema.return_value = {"required_attributes": ["fabric", "color"]}
        res = run_intent_agent(state)
        
        assert res.get("intent_mandate") is None
        assert "fabric" in res["missing_fields"]

@patch("app.agents.agent_intent.call_llm")
def test_intent_agent_unsupported(mock_call):
    mock_call.return_value = '{"category": "car", "constraints": {}}'
    state = ConversationState(raw_query="buy a car", constraints={}, messages=[])
    
    res = run_intent_agent(state)
    assert res.get("unsupported_category") is True
''',
    "tests/test_clarify_loop_cap.py": '''\
import pytest
from unittest.mock import patch
from app.agents.state import ConversationState
from app.agents.agent_clarify import run_clarify_agent

@patch("app.agents.agent_clarify.call_llm")
def test_clarify_caps_at_3(mock_call):
    mock_call.return_value = "What fabric?"
    
    # Round 1
    state = ConversationState(clarify_round=1, missing_fields=["fabric"], constraints={}, messages=[])
    res = run_clarify_agent(state)
    assert res.get("intent_mandate") is None
    assert mock_call.call_count == 1
    
    # Round 3
    state = ConversationState(clarify_round=3, missing_fields=["fabric", "budget_max"], constraints={}, messages=[], category="saree")
    res = run_clarify_agent(state)
    
    assert res.get("intent_mandate") is not None
    assert res["intent_mandate"].completeness == 0.5
    assert res["constraints"]["fabric"] == "any"
    assert res["constraints"]["budget_max"] == 2000.0
    
    # Assert LLM was NOT called on round 3 cap
    assert mock_call.call_count == 1
''',
    "tests/test_agent_to_policy_handoff.py": '''\
import pytest
import uuid
import json
from unittest.mock import patch
from app.agents.state import ConversationState
from app.agents.graph import run_conversation_turn
from app.protocols.ap2.mandates import CartMandate
from app.services.policy_engine import evaluate_payment_authorization

@patch("app.agents.agent_intent.call_llm")
@patch("app.agents.agent_ranking.call_llm")
@patch("app.agents.agent_discovery.SessionLocal")
def test_end_to_end_handoff(mock_db, mock_rank_llm, mock_intent_llm):
    mock_intent_llm.return_value = '{"category": "saree", "constraints": {"budget_max": 2000}}'
    mock_rank_llm.return_value = '[{"product_id": "123e4567-e89b-12d3-a456-426614174000", "rank": 1, "explanation": "best"}]'
    
    class DummyProduct:
        product_id = uuid.UUID("123e4567-e89b-12d3-a456-426614174000")
        category = "saree"
        normalized = {"price": 1500, "stock": True}
        
    mock_session = mock_db.return_value
    mock_session.query().filter().all.return_value = [DummyProduct()]
    
    with patch("app.agents.agent_intent.get_schema") as mock_schema:
        mock_schema.return_value = {"required_attributes": []}
        
        state = ConversationState(raw_query="", constraints={}, messages=[], clarify_round=0)
        final_state = run_conversation_turn(state, "I want a saree")
        
        assert final_state["intent_mandate"] is not None
        assert len(final_state["candidate_products"]) == 1
        
        # Build cart mandate
        cart = CartMandate(
            mandate_id=uuid.uuid4(),
            intent_mandate_id=final_state["intent_mandate"].mandate_id,
            product_id=uuid.UUID(final_state["candidate_products"][0]["id"]),
            price_at_selection=1500,
            payable_amount=1500
        )
        
        # Hand off to Phase 2 policy engine
        decision = evaluate_payment_authorization(final_state["intent_mandate"], cart)
        assert decision.approved is True
        assert decision.authorization_type == "auto"

@patch("app.agents.agent_ranking.call_llm")
@patch("app.agents.agent_discovery.SessionLocal")
def test_skip_llm_if_empty(mock_db, mock_rank_llm):
    mock_session = mock_db.return_value
    mock_session.query().filter().all.return_value = [] # DB returns empty
    
    from app.agents.agent_discovery import run_discovery_agent
    from app.agents.agent_ranking import run_ranking_agent
    from app.protocols.ap2.mandates import IntentMandate
    
    state = ConversationState(
        intent_mandate=IntentMandate(mandate_id=uuid.uuid4(), user_id="u", category="saree", constraints={}, autopay_limit=2000, completeness=1.0)
    )
    
    state = run_discovery_agent(state)
    assert state.get("candidate_products") == []
    
    state = run_ranking_agent(state)
    assert mock_rank_llm.call_count == 0
'''
}

for path, content in files.items():
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
