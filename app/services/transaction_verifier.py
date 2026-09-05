import logging
from uuid import UUID
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.models import PaymentMandate
from app.mcp.razorpay_client import RazorpayClientError
from app.core.tool_gateway import execute_tool_call
from app.services.audit_ledger import write_audit_log
from app.services.order_service import create_order_from_mandate

logger = logging.getLogger(__name__)

class ReconciliationResult(BaseModel):
    status: str
    action_taken: str

def reconcile_payment(db: Session, payment_mandate_id: UUID) -> ReconciliationResult:
    """
    Handles Razorpay webhook delays or mismatches by treating the Provider as the Source of Truth.
    """
    mandate = db.query(PaymentMandate).filter_by(mandate_id=payment_mandate_id).first()
    if not mandate:
        raise ValueError("Payment Mandate not found.")
        
    if mandate.status in ('captured', 'refunded'):
        return ReconciliationResult(status=mandate.status, action_taken="none")
        
    if not mandate.razorpay_order_id:
        return ReconciliationResult(status=mandate.status, action_taken="none_no_order")

    try:
        provider_state = execute_tool_call(
            agent_name="transaction_verifier",
            tool_name="razorpay_fetch_order",
            arguments={"order_id": mandate.razorpay_order_id}
        )
        provider_status = provider_state.get("status")
        
        if provider_status in ('paid', 'captured') and mandate.status == 'pending':
            mandate.status = 'captured'
            
            # Atomic stock decrement via order service
            success = create_order_from_mandate(db, mandate.cart_mandate_id, mandate.mandate_id)
            if not success:
                write_audit_log(
                    db=db, agent_name="TransactionVerifier", event_type="oversell_detected", reference_id=payment_mandate_id,
                    input_snapshot={}, output_snapshot={},
                    reasoning="Payment captured but product was out of stock. Needs manual refund/merchant review."
                )
            
            write_audit_log(
                db=db, agent_name="TransactionVerifier", event_type="reconciled", reference_id=payment_mandate_id,
                input_snapshot={"provider_status": provider_status}, output_snapshot={"new_status": "captured"},
                reasoning="webhook delayed, confirmed via poll"
            )
            db.commit()
            return ReconciliationResult(status='captured', action_taken="updated_to_captured")
            
        elif provider_status == 'failed' and mandate.status == 'pending':
            mandate.status = 'failed'
            write_audit_log(
                db=db, agent_name="TransactionVerifier", event_type="reconciled", reference_id=payment_mandate_id,
                input_snapshot={"provider_status": provider_status}, output_snapshot={"new_status": "failed"},
                reasoning="webhook delayed, confirmed failure via poll"
            )
            db.commit()
            return ReconciliationResult(status='failed', action_taken="updated_to_failed")
            
        elif provider_status in ('paid', 'captured') and mandate.status == 'failed':
            # Edge case: we gave up too early
            write_audit_log(
                db=db, agent_name="TransactionVerifier", event_type="reconciliation_warning", reference_id=payment_mandate_id,
                input_snapshot={"provider_status": provider_status, "internal_status": mandate.status}, output_snapshot={},
                reasoning="WARNING: Provider paid but internal status failed. Manual review required."
            )
            db.commit()
            return ReconciliationResult(status='failed', action_taken="flagged_for_review")
            
    except RazorpayClientError as e:
        logger.error(f"Reconciliation failed to fetch status: {e}")
        
    return ReconciliationResult(status=mandate.status, action_taken="no_change")
