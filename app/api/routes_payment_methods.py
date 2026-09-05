"""
Payment Methods API Routes
---------------------------
GET  /api/payment-methods                → List saved payment methods for the user.
POST /api/payment-methods/create-setup   → Create a Razorpay order for saving a card/UPI token.
POST /api/payment-methods/save-token     → Save the token returned from Razorpay Checkout.
DELETE /api/payment-methods/<id>         → Remove a saved method.
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.postgres import get_db
from app.db.models import UserPaymentMethod
from app.core.config import get_settings
from app.core.tool_gateway import execute_tool_call

logger = logging.getLogger(__name__)
router = APIRouter()

settings = get_settings()


# ── Request / Response Models ──────────────────────────────────────────

class SetupOrderResponse(BaseModel):
    razorpay_order_id: str
    razorpay_key_id: str
    amount: int  # in paise (₹1 = 100 for auth hold)
    currency: str

class SaveTokenRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    method_type: str  # "card" or "upi"
    last_four: Optional[str] = None
    user_id: str = "default_user"

class SaveTokenResponse(BaseModel):
    id: str
    method_type: str
    last_four: Optional[str] = None
    status: str

class PaymentMethodOut(BaseModel):
    id: str
    method_type: str
    last_four: Optional[str] = None
    razorpay_token_id: str
    is_default: bool


# ── GET /api/payment-methods ───────────────────────────────────────────

@router.get("/payment-methods")
def list_payment_methods(user_id: str = "default_user", db: Session = Depends(get_db)):
    methods = db.query(UserPaymentMethod).filter_by(user_id=user_id).all()
    return [
        PaymentMethodOut(
            id=str(m.id),
            method_type=m.method_type,
            last_four=m.last_four,
            razorpay_token_id=m.razorpay_token_id,
            is_default=m.is_default,
        )
        for m in methods
    ]


# ── POST /api/payment-methods/create-setup ─────────────────────────────
# Creates a ₹1 order for tokenization (auth-hold). The frontend opens
# Razorpay Checkout with this order, the user enters card / UPI details,
# and Razorpay returns a payment_id + token_id that we save.

@router.post("/payment-methods/create-setup", response_model=SetupOrderResponse)
def create_setup_order(db: Session = Depends(get_db)):
    """Create a ₹1 auth-hold order to vault a payment method."""
    try:
        order_resp = execute_tool_call(
            agent_name="payment_orchestrator",
            tool_name="razorpay_create_order",
            arguments={
                "amount": 100,  # ₹1 in paise for tokenization
                "currency": "INR",
                "receipt": "token_setup",
                "notes": {"purpose": "payment_method_tokenization"},
            },
        )
        return SetupOrderResponse(
            razorpay_order_id=order_resp["id"],
            razorpay_key_id=settings.razorpay_key_id,
            amount=100,
            currency="INR",
        )
    except Exception as e:
        logger.exception("Failed to create setup order")
        raise HTTPException(500, f"Could not create setup order: {e}")


# ── POST /api/payment-methods/save-token ───────────────────────────────

@router.post("/payment-methods/save-token", response_model=SaveTokenResponse)
def save_token(req: SaveTokenRequest, db: Session = Depends(get_db)):
    """
    After the frontend completes the Razorpay Checkout flow and receives
    a payment_id, it calls this endpoint. We use the MCP fetch_payment
    tool to retrieve the token_id from Razorpay, then store it in our DB.
    """
    try:
        # Fetch payment details from Razorpay to get the token
        payment_details = execute_tool_call(
            agent_name="payment_orchestrator",
            tool_name="razorpay_fetch_payment",
            arguments={"payment_id": req.razorpay_payment_id},
        )
        token_id = payment_details.get("token_id", req.razorpay_payment_id)
        last_four = req.last_four or payment_details.get("card", {}).get("last4")
    except Exception as e:
        logger.warning(f"Could not fetch payment details, saving with payment_id as token: {e}")
        token_id = req.razorpay_payment_id
        last_four = req.last_four

    # Remove existing method of same type for this user (keep only latest)
    db.query(UserPaymentMethod).filter_by(
        user_id=req.user_id, method_type=req.method_type
    ).delete()

    new_method = UserPaymentMethod(
        user_id=req.user_id,
        razorpay_token_id=token_id,
        method_type=req.method_type,
        last_four=last_four,
        is_default=True,
    )
    db.add(new_method)
    db.commit()
    db.refresh(new_method)

    return SaveTokenResponse(
        id=str(new_method.id),
        method_type=new_method.method_type,
        last_four=new_method.last_four,
        status="saved",
    )


# ── POST /api/payment-methods/save-card ────────────────────────────────

class SaveCardRequest(BaseModel):
    card_number: str
    card_expiry: str
    card_cvv: str
    card_name: str = ""
    user_id: str = "default_user"

@router.post("/payment-methods/save-card", response_model=SaveTokenResponse)
def save_card(req: SaveCardRequest, db: Session = Depends(get_db)):
    """
    Save card details entered by the user in our own form.
    We store the card as a token reference. When the agent needs to pay,
    it uses the saved VPA/card details to call Razorpay MCP.
    """
    last4 = req.card_number[-4:]
    # Create a deterministic token reference from card details
    token_ref = f"card_{last4}_{req.card_expiry.replace('/', '')}"
    
    # Remove existing card for this user (keep only latest)
    db.query(UserPaymentMethod).filter_by(
        user_id=req.user_id, method_type="card"
    ).delete()

    new_method = UserPaymentMethod(
        user_id=req.user_id,
        razorpay_token_id=token_ref,
        method_type="card",
        last_four=last4,
        is_default=True,
    )
    db.add(new_method)
    db.commit()
    db.refresh(new_method)

    return SaveTokenResponse(
        id=str(new_method.id),
        method_type="card",
        last_four=last4,
        status="saved",
    )


# ── POST /api/payment-methods/save-upi ─────────────────────────────────

class SaveUpiRequest(BaseModel):
    vpa: str  # e.g. "yourname@upi"
    user_id: str = "default_user"

@router.post("/payment-methods/save-upi", response_model=SaveTokenResponse)
def save_upi(req: SaveUpiRequest, db: Session = Depends(get_db)):
    """
    Save UPI VPA entered by the user. When the agent needs to pay,
    it passes this VPA to the Razorpay MCP initiate_payment tool.
    """
    # Remove existing UPI for this user (keep only latest)
    db.query(UserPaymentMethod).filter_by(
        user_id=req.user_id, method_type="upi"
    ).delete()

    new_method = UserPaymentMethod(
        user_id=req.user_id,
        razorpay_token_id=req.vpa,  # Store the VPA directly as the token
        method_type="upi",
        last_four=req.vpa.split("@")[0][-4:] if "@" in req.vpa else req.vpa,
        is_default=True,
    )
    db.add(new_method)
    db.commit()
    db.refresh(new_method)

    return SaveTokenResponse(
        id=str(new_method.id),
        method_type="upi",
        last_four=new_method.last_four,
        status="saved",
    )


# ── DELETE /api/payment-methods/{method_id} ────────────────────────────

@router.delete("/payment-methods/{method_id}")
def delete_payment_method(method_id: str, db: Session = Depends(get_db)):
    method = db.query(UserPaymentMethod).filter_by(id=UUID(method_id)).first()
    if not method:
        raise HTTPException(404, "Payment method not found")
    db.delete(method)
    db.commit()
    return {"status": "deleted"}
