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
@patch("app.agents.agent_discovery.discover_products")
@patch("app.agents.agent_discovery.attach_effective_pricing")
@patch("app.agents.agent_discovery.write_audit_log")
def test_end_to_end_handoff(mock_audit, mock_attach, mock_discover, mock_rank_llm, mock_intent_llm):
    mock_intent_llm.return_value = '{"category": "saree", "constraints": {"budget_max": 2000}}'
    mock_rank_llm.return_value = '[{"product_id": "123e4567-e89b-12d3-a456-426614174000", "rank": 1, "explanation": "best"}]'
    
    mock_discover.return_value = [
        {"id": "123e4567-e89b-12d3-a456-426614174000", "merchant_id": "m1", "category": "saree", "price": 1500, "stock": True}
    ]
    mock_attach.side_effect = lambda x: x
    
    mock_discover.return_value = [
        {"id": "123e4567-e89b-12d3-a456-426614174000", "merchant_id": "m1", "category": "saree", "price": 1500, "stock": True}
    ]
    
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
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value.category = 'saree'
        decision = evaluate_payment_authorization(mock_db, final_state["intent_mandate"], cart)
        assert decision.approved is True
        assert decision.authorization_type == "auto"

@patch("app.agents.agent_ranking.call_llm")
@patch("app.agents.agent_discovery.discover_products")
@patch("app.agents.agent_discovery.attach_effective_pricing")
@patch("app.agents.agent_discovery.write_audit_log")
def test_skip_llm_if_empty(mock_audit, mock_attach, mock_discover, mock_rank_llm):
    mock_discover.return_value = []
    mock_attach.side_effect = lambda x: x
    
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
