import logging
from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.models import PaymentMandate
from app.mcp.razorpay_client import RazorpayClientError
from app.core.tool_gateway import execute_tool_call
from app.services.audit_ledger import write_audit_log

logger = logging.getLogger(__name__)



class RefundResult(BaseModel):
    status: str
    refund_id: str | None = None

def handle_cancellation(db: Session, payment_mandate_id: UUID, reason: str) -> RefundResult:
    """User-initiated cancel. Only permitted if status == 'captured'."""
    mandate = db.query(PaymentMandate).filter_by(mandate_id=payment_mandate_id).first()
    if not mandate:
        raise ValueError("Payment Mandate not found.")
        
    if mandate.status != 'captured':
        raise ValueError("Cannot refund a mandate that is not captured.")
        
    try:
        import requests, os, base64
        key_id = os.getenv('RAZORPAY_KEY_ID')
        key_secret = os.getenv('RAZORPAY_KEY_SECRET')
        
        # Payment ID to refund
        payment_id = mandate.razorpay_payment_id
        
        if not payment_id or not payment_id.startswith('pay_'):
            # If the user paid manually, we saved the real pay_ ID. If it was mocked or order only, we can't refund.
            raise ValueError("No valid payment ID to refund.")

        res = requests.post(
            f'https://api.razorpay.com/v1/payments/{payment_id}/refund',
            auth=(key_id, key_secret),
            json={"amount": int(float(mandate.amount) * 100)}  # Paise
        )
        
        if res.status_code >= 400:
            raise ValueError(f"Refund failed: {res.json().get('error', {}).get('description', res.text)}")
            
        refund_resp = res.json()

        mandate.status = 'pending_refund'
        write_audit_log(
            db=db, agent_name="RecoveryService", event_type="refund_requested", reference_id=payment_mandate_id,
            input_snapshot={"reason": reason}, output_snapshot={"refund_id": refund_resp.get("id")},
            reasoning=f"User initiated cancel, refund pending settlement: {reason}"
        )
        db.commit()
        return RefundResult(status="pending_refund", refund_id=refund_resp.get("id"))
    except Exception as e:
        write_audit_log(
            db=db, agent_name="RecoveryService", event_type="refund_failed", reference_id=payment_mandate_id,
            input_snapshot={"reason": reason}, output_snapshot={"error": str(e)},
            reasoning="Refund API call failed."
        )
        db.commit()
        raise e

def auto_refund_on_oversell(db: Session, payment_mandate_id: UUID, reason: str) -> Optional[RefundResult]:
    """
    Called automatically (not manually) when decrement_stock_atomic returns False
    AFTER a payment was already captured -- the item sold out between ranking and
    payment completion. This must refund WITHOUT requiring a human to notice and
    trigger it manually.
    """
    db_mandate = db.query(PaymentMandate).filter_by(mandate_id=payment_mandate_id).first()
    if not db_mandate or db_mandate.status != "captured":
        return None  # nothing to refund

    try:
        import requests, os
        key_id = os.getenv('RAZORPAY_KEY_ID')
        key_secret = os.getenv('RAZORPAY_KEY_SECRET')
        
        payment_id = db_mandate.razorpay_payment_id
        if not payment_id or not payment_id.startswith('pay_'):
            raise ValueError("No valid payment ID to refund.")

        res = requests.post(
            f'https://api.razorpay.com/v1/payments/{payment_id}/refund',
            auth=(key_id, key_secret),
            json={"amount": int(float(db_mandate.amount) * 100), "notes": {"reason": reason}}
        )
        
        if res.status_code >= 400:
            raise ValueError(f"Refund failed: {res.json().get('error', {}).get('description', res.text)}")
            
        refund_result = res.json()

        db_mandate.status = "refunded"
        db.commit()
        write_audit_log(
            db, "RecoveryService", "auto_refund_success", payment_mandate_id,
            {"reason": reason}, {"refund_id": refund_result.get("id")},
            f"Automatically refunded due to: {reason}"
        )
        return RefundResult(status="refunded", refund_id=refund_result.get("id"))
    except Exception as e:
        write_audit_log(
            db, "RecoveryService", "auto_refund_failed", payment_mandate_id,
            {"reason": reason}, None,
            f"CRITICAL: automatic refund failed after oversell: {e}. Requires manual merchant intervention."
        )
        raise

def reconcile_payment(db: Session, payment_mandate_id: UUID) -> None:
    """
    Reconciles a failed or unknown payment state.
    """
    db_mandate = db.query(PaymentMandate).filter_by(mandate_id=payment_mandate_id).first()
    if not db_mandate:
        return
        
    write_audit_log(
        db, "RecoveryService", "reconciliation_run", payment_mandate_id,
        None, None, f"Reconciliation executed for payment state: {db_mandate.status}"
    )

