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
    missing_field_options: Dict[str, Any]
    unsupported_category: bool
    user_autopay_limit: Optional[float]
    user_mandate_limit: Optional[float]
    user_payment_method: Optional[str]

def rehydrate_state(raw_state: dict) -> "ConversationState":
    """
    Client-echoed state arrives as plain dicts (JSON round-trip). Re-hydrate any
    mandate fields into their proper Pydantic models before agents touch them,
    since agents access these via attribute (e.g. .category, .autopay_limit),
    not dict subscript.
    """
    from app.protocols.ap2.mandates import IntentMandate, CartMandate
    state = dict(raw_state)
    im = state.get("intent_mandate")
    if isinstance(im, dict):
        state["intent_mandate"] = IntentMandate(**im)
    cm = state.get("cart_mandate")
    if isinstance(cm, dict):
        state["cart_mandate"] = CartMandate(**cm)
    return state
