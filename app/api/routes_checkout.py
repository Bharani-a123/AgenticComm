"""
Checkout API Routes
--------------------
POST /api/checkout         → Execute or request confirmation for a purchase.
POST /api/checkout/confirm → Finalise a user-confirmed purchase.

These endpoints use the pre-assembled CartMandates (created by the ranking
pipeline) and the existing PaymentExecutor + PolicyEngine infrastructure.
"""
import uuid
import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.postgres import get_db
from app.db.models import (
    CartMandate as DBCartMandate,
    IntentMandate as DBIntentMandate,
)
from app.protocols.ap2.mandates import IntentMandate, CartMandate, PaymentMandate
from app.services.policy_engine import (
    evaluate_payment_authorization,
    confirm_user_authorization,
)
from app.services.payment_executor import execute_payment, PaymentExecutionError
from app.services.payment_orchestrator import orchestrate_payment
from app.services.audit_ledger import write_audit_log

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request / Response models ────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    cart_mandate_id: str   # UUID string — from the product card
    user_id: str = "demo_user"
    user_payment_method: Optional[str] = None

class CheckoutConfirmRequest(BaseModel):
    cart_mandate_id: str
    confirmed: bool
    user_id: str = "demo_user"
    user_payment_method: Optional[str] = None

class CancelRequest(BaseModel):
    cart_mandate_id: str
    reason: str = "User requested refund"

class CheckoutResponse(BaseModel):
    status: str                          # "auto_paid" | "needs_confirmation" | "rejected" | "error"
    razorpay_order_id: Optional[str] = None
    payable_amount: Optional[float] = None
    authorization_type: Optional[str] = None
    reason: Optional[str] = None


# ── POST /api/checkout ───────────────────────────────────────────────────

@router.post("/checkout", response_model=CheckoutResponse)
def checkout_endpoint(req: CheckoutRequest, db: Session = Depends(get_db)):
    """
    Called when the user clicks a product's Buy/Confirm button.
    1. Look up pre-created CartMandate + parent IntentMandate from DB.
    2. Evaluate PolicyDecision.
    3. If auto-approved → execute payment immediately via Razorpay MCP.
    4. If user_confirmed → return confirmation prompt (frontend shows dialog).
    5. If rejected → return rejection.
    """
    try:
        cart_uuid = uuid.UUID(req.cart_mandate_id)
    except ValueError:
        raise HTTPException(400, "Invalid cart_mandate_id")

    # Fetch CartMandate
    db_cart = db.query(DBCartMandate).filter_by(mandate_id=cart_uuid).first()
    if not db_cart:
        raise HTTPException(404, "Cart mandate not found. Product may have expired.")

    # Fetch parent IntentMandate
    db_intent = (
        db.query(DBIntentMandate)
        .filter_by(mandate_id=db_cart.intent_mandate_id)
        .first()
    )
    if not db_intent:
        raise HTTPException(404, "Intent mandate not found.")

    # Prepare constraints
    constraints = dict(db_intent.constraints)

    # Rehydrate Pydantic models
    intent = IntentMandate(
        mandate_id=db_intent.mandate_id,
        user_id=db_intent.user_id,
        category=db_intent.category,
        constraints=constraints,
        autopay_limit=float(db_intent.constraints.get("_autopay_limit", 0.0)),
        completeness=float(db_intent.completeness),
    )
    cart = CartMandate(
        mandate_id=db_cart.mandate_id,
        intent_mandate_id=db_cart.intent_mandate_id,
        product_id=db_cart.product_id,
        price_at_selection=float(db_cart.price_at_selection),
        coupon_id=db_cart.coupon_id,
        payable_amount=float(db_cart.payable_amount),
    )

    # Evaluate policy
    policy = evaluate_payment_authorization(db, intent, cart)

    if policy.authorization_type == "rejected":
        write_audit_log(
            db, "checkout_api", "payment_rejected", cart.mandate_id,
            {"amount": cart.payable_amount}, None, policy.reason,
        )
        return CheckoutResponse(
            status="rejected",
            payable_amount=cart.payable_amount,
            authorization_type="rejected",
            reason=policy.reason,
        )

    if policy.authorization_type == "user_confirmed":
        # Don't execute yet — return prompt for frontend to show confirm dialog
        return CheckoutResponse(
            status="needs_confirmation",
            payable_amount=cart.payable_amount,
            authorization_type="user_confirmed",
            reason=policy.reason,
        )

    # Auto-approved → execute immediately
    result = orchestrate_payment(db, cart, policy, intent, req.user_payment_method)
    return CheckoutResponse(
        status="auto_paid" if result.status == "captured" else result.status,
        razorpay_order_id=result.razorpay_order_id,
        payable_amount=result.payable_amount,
        authorization_type=result.authorization_type,
        reason=result.reason
    )


# ── POST /api/checkout/confirm ───────────────────────────────────────────

@router.post("/checkout/confirm", response_model=CheckoutResponse)
def checkout_confirm_endpoint(req: CheckoutConfirmRequest, db: Session = Depends(get_db)):
    """Handle user's explicit yes/no on the confirmation dialog."""
    try:
        cart_uuid = uuid.UUID(req.cart_mandate_id)
    except ValueError:
        raise HTTPException(400, "Invalid cart_mandate_id")

    db_cart = db.query(DBCartMandate).filter_by(mandate_id=cart_uuid).first()
    if not db_cart:
        raise HTTPException(404, "Cart mandate not found.")

    db_intent = (
        db.query(DBIntentMandate)
        .filter_by(mandate_id=db_cart.intent_mandate_id)
        .first()
    )
    if not db_intent:
        raise HTTPException(404, "Intent mandate not found.")

    # Prepare constraints
    constraints = dict(db_intent.constraints)

    intent = IntentMandate(
        mandate_id=db_intent.mandate_id,
        user_id=db_intent.user_id,
        category=db_intent.category,
        constraints=constraints,
        autopay_limit=float(db_intent.constraints.get("_autopay_limit", 0.0)),
        completeness=float(db_intent.completeness),
    )
    cart = CartMandate(
        mandate_id=db_cart.mandate_id,
        intent_mandate_id=db_cart.intent_mandate_id,
        product_id=db_cart.product_id,
        price_at_selection=float(db_cart.price_at_selection),
        coupon_id=db_cart.coupon_id,
        payable_amount=float(db_cart.payable_amount),
    )

    # Re-evaluate base policy, then apply user confirmation
    base_policy = evaluate_payment_authorization(db, intent, cart)
    final_policy = confirm_user_authorization(base_policy, req.confirmed)

    if not final_policy.approved:
        write_audit_log(
            db, "checkout_api", "user_denied_payment", cart.mandate_id,
            {"amount": cart.payable_amount}, None, final_policy.reason,
        )
        return CheckoutResponse(
            status="rejected",
            payable_amount=cart.payable_amount,
            authorization_type="rejected",
            reason=final_policy.reason,
        )

    result = orchestrate_payment(db, cart, final_policy, intent, req.user_payment_method)
    return CheckoutResponse(
        status="auto_paid" if result.status == "captured" else result.status,
        razorpay_order_id=result.razorpay_order_id,
        payable_amount=result.payable_amount,
        authorization_type=result.authorization_type,
        reason=result.reason
    )

@router.post("/checkout/cancel")
def cancel_checkout_endpoint(req: CancelRequest, db: Session = Depends(get_db)):
    """User initiated cancellation & refund."""
    from app.services.recovery_service import handle_cancellation
    from app.db.models import PaymentMandate
    from uuid import UUID
    
    # We only have cart_mandate_id. We need payment_mandate_id.
    payment_mandate = db.query(PaymentMandate).filter_by(cart_mandate_id=UUID(req.cart_mandate_id)).first()
    if not payment_mandate:
        raise HTTPException(404, "Payment Mandate not found for this Cart.")
        
    try:
        res = handle_cancellation(db, payment_mandate.mandate_id, req.reason)
        return res.model_dump()
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Cancel failed: {e}")
        raise HTTPException(500, "Refund processing failed.")
