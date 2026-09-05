import logging
import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.models import PaymentMandate as DBPaymentMandate
from app.protocols.ap2.mandates import PaymentMandate
from app.services.policy_engine import PolicyDecision
from app.core.tool_gateway import execute_tool_call
from app.services.audit_ledger import write_audit_log
from app.db.redis import get_redis
from app.services.recovery_service import auto_refund_on_oversell, reconcile_payment
from app.services.order_service import get_product_id_for_cart, decrement_stock_atomic

logger = logging.getLogger(__name__)

class PaymentExecutionError(Exception):
    pass

class PaymentResult(BaseModel):
    status: str
    razorpay_order_id: Optional[str] = None

def execute_payment(db: Session, payment_mandate: PaymentMandate, policy_decision: PolicyDecision) -> PaymentResult:
    if not policy_decision.approved:
        raise PaymentExecutionError("Cannot execute an unapproved payment mandate.")

    # Idempotency key must be deterministic, derived from cart_mandate_id
    idempotency_key = payment_mandate.idempotency_key

    # Idempotency check FIRST — if this cart was already paid, return the existing result
    existing = db.query(DBPaymentMandate).filter_by(idempotency_key=idempotency_key).first()
    if existing and existing.status == "captured":
        write_audit_log(
            db, "PaymentExecutor", "idempotent_replay", payment_mandate.cart_mandate_id,
            {"idempotency_key": idempotency_key}, {"existing_status": existing.status},
            "Payment already captured for this cart -- returning cached result, not re-charging."
        )
        return PaymentResult(status=existing.status, razorpay_order_id=existing.razorpay_order_id)

    redis_client = get_redis()
    redis_lock_key = f"lock:payment:{idempotency_key}"
    lock_acquired = redis_client.set(redis_lock_key, "1", nx=True, ex=30)
    if not lock_acquired:
        raise PaymentExecutionError("Payment already in progress for this cart. Please wait.")

    try:
        # 1. CREATE ORDER
        # Use existing order if we are retrying a pending payment, to avoid spamming orders
        razorpay_order_id = existing.razorpay_order_id if existing else None
        
        if not razorpay_order_id:
            order_result = execute_tool_call(
                agent_name="payment_orchestrator",
                tool_name="razorpay_create_order",
                arguments={
                    "amount": int(payment_mandate.amount * 100),  # Razorpay expects paise, not rupees
                    "currency": "INR",
                    "receipt": idempotency_key,
                    "notes": {"cart_mandate_id": str(payment_mandate.cart_mandate_id)}
                }
            )
            razorpay_order_id = order_result.get("id") or order_result.get("order_id")

        if existing:
            db_mandate = existing
            db_mandate.razorpay_order_id = razorpay_order_id
            db_mandate.status = "pending"
        else:
            db_mandate = DBPaymentMandate(
                mandate_id=payment_mandate.mandate_id,
                cart_mandate_id=payment_mandate.cart_mandate_id,
                amount=payment_mandate.amount,
                authorization_type=policy_decision.authorization_type,
                razorpay_order_id=razorpay_order_id,
                status="pending",
                idempotency_key=idempotency_key,
            )
            db.add(db_mandate)
        
        db.commit()

        write_audit_log(
            db, "PaymentExecutor", "order_created", payment_mandate.cart_mandate_id,
            {"amount": payment_mandate.amount}, {"razorpay_order_id": razorpay_order_id},
            f"Order created automatically: {policy_decision.reason}"
        )

        # 2. AUTOMATIC CAPTURE via S2S UPI Collect
        from app.db.models import CartMandate, IntentMandate
        from app.mcp.razorpay_client import create_upi_collect_payment
        import time
        import requests
        
        cart_db = db.query(CartMandate).filter_by(mandate_id=payment_mandate.cart_mandate_id).first()
        intent_db = db.query(IntentMandate).filter_by(mandate_id=cart_db.intent_mandate_id).first()
        user_id = intent_db.user_id

        # Use dummy email/contact for test mode
        user_email = f"{user_id}@test.com"
        user_contact = "9999999999"

        charge_result = create_upi_collect_payment(
            order_id=razorpay_order_id,
            amount=payment_mandate.amount,
            email=user_email,
            contact=user_contact,
            vpa="success@razorpay" # Always succeeds in test mode (in theory)
        )

        razorpay_payment_id = charge_result.get("razorpay_payment_id")
        if not razorpay_payment_id:
            raise Exception(f"Razorpay capture failed. No payment_id in response: {charge_result}")
            
        # Optional: Polling logic hitting the "next" URL
        poll_url = None
        for next_action in charge_result.get("next", []):
            if next_action.get("action") == "poll":
                poll_url = next_action.get("url")
                break
                
        if poll_url:
            for _ in range(5):
                time.sleep(2)
                poll_res = requests.get(poll_url)
                if poll_res.status_code == 200:
                    status_data = poll_res.json()
                    if status_data.get("status") in ["captured", "authorized"]:
                        break
                    elif status_data.get("status") == "failed":
                        raise Exception("UPI payment failed during polling.")
                else:
                    break

        db_mandate.razorpay_payment_id = razorpay_payment_id
        db_mandate.status = "captured"
        db_mandate.authorized_at = datetime.utcnow()
        db.commit()

        write_audit_log(
            db, "PaymentExecutor", "payment_captured", payment_mandate.cart_mandate_id,
            {"razorpay_order_id": razorpay_order_id}, {"status": "captured"},
            "Payment automatically captured after successful order creation."
        )

        # 3. AUTOMATIC STOCK DECREMENT
        product_id = get_product_id_for_cart(db, payment_mandate.cart_mandate_id)
        if not decrement_stock_atomic(db, product_id):
            # Stock decrement failed after payment capture! Trigger auto refund.
            auto_refund_on_oversell(db, payment_mandate.mandate_id, f"Stock unavailable for product {product_id} after capture.")
            raise PaymentExecutionError("Item oversold. Payment captured but stock exhausted. Automatic refund issued.")

        return PaymentResult(status="captured", razorpay_order_id=razorpay_order_id)

    except Exception as e:
        db.rollback()
        write_audit_log(
            db, "PaymentExecutor", "payment_failed", payment_mandate.cart_mandate_id,
            None, None, f"Payment failed: {e}. Triggering automatic recovery."
        )

        # 4. AUTOMATIC GRACEFUL RECOVERY
        try:
            reconcile_payment(db, payment_mandate.mandate_id)
        except Exception as recovery_error:
            write_audit_log(
                db, "PaymentExecutor", "recovery_failed", payment_mandate.cart_mandate_id,
                None, None, f"Automatic recovery also failed: {recovery_error}. Needs manual review."
            )

        raise PaymentExecutionError(str(e)) from e
    finally:
        redis_client.delete(redis_lock_key)


