import uuid
import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.protocols.ap2.mandates import IntentMandate, CartMandate, PaymentMandate
from app.services.policy_engine import PolicyDecision
from app.services.payment_executor import execute_payment, PaymentExecutionError
from app.services.audit_ledger import write_audit_log

from app.protocols.ap2.adapter import create_payment_mandate

logger = logging.getLogger(__name__)

class OrchestrationResult:
    def __init__(self, status: str, razorpay_order_id: Optional[str] = None, payable_amount: Optional[float] = None, authorization_type: Optional[str] = None, reason: Optional[str] = None):
        self.status = status
        self.razorpay_order_id = razorpay_order_id
        self.payable_amount = payable_amount
        self.authorization_type = authorization_type
        self.reason = reason

def orchestrate_payment(db: Session, cart: CartMandate, policy: PolicyDecision, intent: IntentMandate, payment_method: Optional[str] = None) -> OrchestrationResult:
    """
    Payment Orchestrator Agent logic.
    Converts CartMandate to PaymentMandate via AP2 semantics, and calls Payment Service.
    """
    payment = create_payment_mandate(cart, policy)

    try:
        result = execute_payment(db, payment, policy)
        pm = payment_method or "card_4242"
        write_audit_log(
            db, "payment_orchestrator", "payment_initiated", payment.mandate_id,
            {"amount": payment.amount, "auth": policy.authorization_type, "method": pm},
            {"razorpay_order_id": result.razorpay_order_id, "status": result.status},
            f"Payment initiated autonomously using payment method {pm}: {policy.reason}",
        )
        return OrchestrationResult(
            status="auto_paid" if policy.authorization_type == "auto" else "confirmed_paid",
            razorpay_order_id=result.razorpay_order_id,
            payable_amount=payment.amount,
            authorization_type=policy.authorization_type,
            reason=policy.reason,
        )
    except PaymentExecutionError as e:
        logger.error("Payment execution failed: %s", e)
        return OrchestrationResult(
            status="error",
            payable_amount=payment.amount,
            reason=str(e),
        )
