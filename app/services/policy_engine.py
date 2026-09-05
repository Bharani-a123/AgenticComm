from typing import Literal
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.protocols.ap2.mandates import IntentMandate, CartMandate

class PolicyDecision(BaseModel):
    approved: bool
    authorization_type: Literal["auto", "user_confirmed", "rejected"]
    reason: str

def evaluate_payment_authorization(
    db: Session,
    intent_mandate: IntentMandate,
    cart_mandate: CartMandate,
) -> PolicyDecision:
    """
    Returns a PolicyDecision indicating whether the payment can proceed automatically.
    
    THIS FUNCTION MUST NEVER BE CALLED WITH LLM-GENERATED NUMBERS FOR THE LIMIT COMPARISON.
    autopay_limit and payable_amount must both originate from validated Pydantic models /
    DB values, never raw LLM output.
    """
    from app.db.models import Product
    
    if cart_mandate.payable_amount <= 0:
        return PolicyDecision(approved=False, authorization_type="rejected", reason="invalid amount")
        
    mandate_limit = intent_mandate.constraints.get("user_mandate_limit", float("inf"))
    if cart_mandate.payable_amount > mandate_limit:
        return PolicyDecision(
            approved=False,
            authorization_type="rejected",
            reason=f"Amount {cart_mandate.payable_amount} exceeds hard mandate limit {mandate_limit}"
        )
        
    product = db.query(Product).filter_by(product_id=cart_mandate.product_id).first()
    if not product:
        return PolicyDecision(approved=False, authorization_type="rejected", reason="Product not found")
        
    if intent_mandate.category and product.category != intent_mandate.category:
        return PolicyDecision(
            approved=False,
            authorization_type="rejected",
            reason=f"Product category {product.category} does not match intent category {intent_mandate.category}"
        )
        
    if cart_mandate.payable_amount > intent_mandate.autopay_limit:
        return PolicyDecision(
            approved=False, 
            authorization_type="user_confirmed", 
            reason=f"Amount {cart_mandate.payable_amount} exceeds autopay limit {intent_mandate.autopay_limit}"
        )
        
    return PolicyDecision(
        approved=True,
        authorization_type="auto",
        reason=f"Auto-approved: amount {cart_mandate.payable_amount} within autopay limit {intent_mandate.autopay_limit}"
    )

def confirm_user_authorization(policy_decision: PolicyDecision, user_confirmed: bool) -> PolicyDecision:
    """
    Takes a pending user_confirmed decision + the user's actual yes/no,
    returns final approved=True/False. This is the ONLY path that can flip
    an over-limit payment to approved, and it requires an explicit bool input —
    never inferred from free text.
    """
    if policy_decision.authorization_type != "user_confirmed":
        return policy_decision
        
    if user_confirmed:
        return PolicyDecision(
            approved=True,
            authorization_type="user_confirmed",
            reason=f"{policy_decision.reason} - User explicitly confirmed."
        )
    
    return PolicyDecision(
        approved=False,
        authorization_type="rejected",
        reason=f"{policy_decision.reason} - User explicitly denied."
    )
