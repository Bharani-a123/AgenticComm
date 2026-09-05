from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List
from uuid import UUID

from app.db.postgres import get_db
from app.db.models import IntentMandate, PaymentMandate, CartMandate
from app.db.models_wallet import UserWallet

router = APIRouter()

class WalletSummaryResponse(BaseModel):
    user_id: str
    total_budget_allocated: float
    total_amount_captured: float
    total_amount_refunded: float
    total_amount_pending_refund: float
    available_budget: float

@router.get('/wallet/summary', response_model=WalletSummaryResponse)
def get_wallet_summary(user_id: str = Query(..., description='User ID'), db: Session = Depends(get_db)):
    wallet = db.query(UserWallet).filter(UserWallet.user_id == user_id).first()
    total_budget = float(wallet.allocated_budget) if wallet else 0.0

    results = (
        db.query(
            PaymentMandate.status,
            func.sum(PaymentMandate.amount).label('total_amount')
        )
        .join(CartMandate, PaymentMandate.cart_mandate_id == CartMandate.mandate_id)
        .join(IntentMandate, CartMandate.intent_mandate_id == IntentMandate.mandate_id)
        .filter(IntentMandate.user_id == user_id)
        .group_by(PaymentMandate.status)
        .all()
    )

    captured = 0.0
    refunded = 0.0
    pending_refund = 0.0

    for status, amount in results:
        if amount is None: continue
        amt = float(amount)
        if status == 'captured':
            captured += amt
        elif status == 'refunded':
            refunded += amt
        elif status == 'pending_refund':
            pending_refund += amt

    # Available budget is what you allocated, minus what is actively captured
    # If a refund is pending, it has not returned to available budget yet.
    net_spent = captured
    available_budget = total_budget - net_spent
    if available_budget < 0:
        available_budget = 0.0

    return WalletSummaryResponse(
        user_id=user_id,
        total_budget_allocated=total_budget,
        total_amount_captured=captured,
        total_amount_refunded=refunded,
        total_amount_pending_refund=pending_refund,
        available_budget=available_budget
    )

@router.post('/wallet/allocate')
def allocate_budget(user_id: str = Body(...), amount: float = Body(...), db: Session = Depends(get_db)):
    wallet = db.query(UserWallet).filter(UserWallet.user_id == user_id).first()
    if not wallet:
        wallet = UserWallet(user_id=user_id, allocated_budget=amount)
        db.add(wallet)
    else:
        wallet.allocated_budget = amount
    db.commit()
    return {'status': 'success'}
