import pytest
from unittest.mock import patch
from app.agents.state import ConversationState
from app.agents.agent_intent import run_intent_agent

@patch("app.agents.agent_intent.call_llm")
def test_intent_agent_complete(mock_call):
    mock_call.return_value = '{"category": "saree", "constraints": {"fabric": "silk", "color": "red"}}'
    state = ConversationState(raw_query="i want a red silk saree", constraints={}, messages=[])
    
    with patch("app.agents.agent_intent.get_schema") as mock_schema:
        mock_schema.return_value = {"required_attributes": {"fabric": [], "color": []}}
        res = run_intent_agent(state)
        
        assert res["intent_mandate"] is not None
        assert res["intent_mandate"].category == "saree"
        assert not res.get("unsupported_category")

@patch("app.agents.agent_intent.call_llm")
def test_intent_agent_partial(mock_call):
    mock_call.return_value = '{"category": "saree", "constraints": {"color": "red"}}'
    state = ConversationState(raw_query="i want a red saree", constraints={}, messages=[])
    
    with patch("app.agents.agent_intent.get_schema") as mock_schema:
        mock_schema.return_value = {"required_attributes": {"fabric": [], "color": []}}
        res = run_intent_agent(state)
        
        assert res.get("intent_mandate") is None
        assert "fabric" in res["missing_fields"]

@patch("app.agents.agent_intent.call_llm")
def test_intent_agent_unsupported(mock_call):
    mock_call.return_value = '{"category": "car", "constraints": {}}'
    state = ConversationState(raw_query="buy a car", constraints={}, messages=[])
    
    res = run_intent_agent(state)
    assert res.get("unsupported_category") is True
