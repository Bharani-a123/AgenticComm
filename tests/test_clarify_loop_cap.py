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
