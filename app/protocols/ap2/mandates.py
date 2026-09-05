from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any
from uuid import UUID

class IntentMandate(BaseModel):
    mandate_id: UUID
    user_id: str
    category: Optional[str] = None
    constraints: Dict[str, Any]
    autopay_limit: float # <-- THIS FIELD IS CRITICAL. Every intent carries its own spending ceiling.
    completeness: float = Field(ge=0, le=1)

class CartMandate(BaseModel):
    mandate_id: UUID
    intent_mandate_id: UUID
    product_id: UUID
    price_at_selection: float
    coupon_id: Optional[UUID] = None
    # payable_amount is frozen at selection time -- do not recompute effective_price at payment time, coupon may have expired/changed since.
    payable_amount: float
    hash: Optional[str] = None

class PaymentMandate(BaseModel):
    mandate_id: UUID
    cart_mandate_id: UUID
    amount: float
    authorization_type: Literal["auto", "user_confirmed"]
    idempotency_key: str
    hash: Optional[str] = None
