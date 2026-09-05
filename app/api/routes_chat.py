from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.agents.state import ConversationState, rehydrate_state
from app.agents.graph import run_conversation_turn

router = APIRouter()

class ChatRequest(BaseModel):
    user_id: str
    message: Optional[str] = None
    state: Optional[Dict[str, Any]] = None

@router.post("/chat")
def chat_endpoint(req: ChatRequest):
    # Retrieve current state from frontend cache or initialize fresh
    current_state = rehydrate_state(req.state) if req.state else ConversationState(
        user_id=req.user_id,
        raw_query="",
        category=None,
        constraints={},
        clarify_round=0,
        intent_mandate=None,
        candidate_products=[],
        selected_product_id=None,
        cart_mandate=None,
        messages=[],
        missing_fields=[],
        missing_field_options={},
        unsupported_category=False
    )
    
    try:
        new_state = run_conversation_turn(current_state, req.message)
        return {"state": new_state, "messages": new_state.get("messages", [])}
    except Exception as e:
        import traceback; traceback.print_exc()

        raise HTTPException(status_code=500, detail=str(e))
