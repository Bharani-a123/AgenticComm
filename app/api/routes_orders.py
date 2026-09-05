from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

from app.db.postgres import get_db
from app.db.models import PaymentMandate, CartMandate, IntentMandate, Product, Merchant

router = APIRouter()

class OrderResponse(BaseModel):
    payment_mandate_id: UUID
    cart_mandate_id: UUID
    intent_mandate_id: UUID
    product_title: str
    payable_amount: float
    status: str
    authorization_type: str
    razorpay_order_id: Optional[str]
    razorpay_payment_id: Optional[str]
    created_at: datetime
    authorized_at: Optional[datetime]

@router.get("/orders", response_model=List[OrderResponse])
def get_user_orders(user_id: str = Query(..., description="User ID to fetch orders for"), db: Session = Depends(get_db)):
    """
    Fetches all orders (Payment Mandates) for a specific user, joined with Product details.
    """
    results = (
        db.query(PaymentMandate, CartMandate, IntentMandate, Product, Merchant)
        .join(CartMandate, PaymentMandate.cart_mandate_id == CartMandate.mandate_id)
        .join(IntentMandate, CartMandate.intent_mandate_id == IntentMandate.mandate_id)
        .join(Product, CartMandate.product_id == Product.product_id)
        .join(Merchant, Product.merchant_id == Merchant.merchant_id)
        .filter(IntentMandate.user_id == user_id)
        .order_by(PaymentMandate.created_at.desc())
        .all()
    )

    orders = []
    for payment, cart, intent, product, merchant in results:
        title = product.normalized.get("title") or product.raw_attributes.get("name") or f"{merchant.name} {product.category.title()}"
        
        orders.append(OrderResponse(
            payment_mandate_id=payment.mandate_id,
            cart_mandate_id=cart.mandate_id,
            intent_mandate_id=intent.mandate_id,
            product_title=title,
            payable_amount=float(payment.amount),
            status=payment.status,
            authorization_type=payment.authorization_type,
            razorpay_order_id=payment.razorpay_order_id,
            razorpay_payment_id=payment.razorpay_payment_id,
            created_at=payment.created_at,
            authorized_at=payment.authorized_at
        ))
        
    return orders
