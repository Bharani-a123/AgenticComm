from fastapi import APIRouter, Request, HTTPException, Depends
import json
from app.services.webhook_verifier import verify_webhook_signature
from app.services.transaction_verifier import reconcile_payment
from app.services.audit_ledger import write_audit_log
from app.db.postgres import get_db
from sqlalchemy.orm import Session
from app.db.models import PaymentMandate

router = APIRouter()

@router.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    """Razorpay Webhook endpoint applying HMAC verification before action."""
    raw_body = await request.body()
    received_signature = request.headers.get("X-Razorpay-Signature", "")
    
    if not verify_webhook_signature(raw_body, received_signature):
        write_audit_log(
            db=db, agent_name="WebhookListener", event_type="webhook_rejected",
            reference_id=None, input_snapshot={"signature": received_signature},
            output_snapshot={}, reasoning="Invalid HMAC signature"
        )
        raise HTTPException(status_code=400, detail="Invalid signature")
        
    try:
        payload = json.loads(raw_body)
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = payment_entity.get("order_id")
        
        # Check if this was a token registration payment
        notes = payment_entity.get("notes", {})
        if notes.get("registration") == "true":
            user_id = notes.get("user_id")
            token_id = payment_entity.get("token_id")
            customer_id = payment_entity.get("customer_id")
            method = payment_entity.get("method")
            card_last4 = payment_entity.get("card", {}).get("last4")

            if user_id and token_id and customer_id:
                from app.db.models import PaymentToken
                existing_token = db.query(PaymentToken).filter_by(user_id=user_id, razorpay_token_id=token_id).first()
                if not existing_token:
                    pt = PaymentToken(
                        user_id=user_id,
                        razorpay_customer_id=customer_id,
                        razorpay_token_id=token_id,
                        card_last4=card_last4,
                        method_type=method or "unknown"
                    )
                    db.add(pt)
                    db.commit()
                    write_audit_log(
                        db=db, agent_name="WebhookListener", event_type="token_registered",
                        reference_id=None, input_snapshot={"token_id": token_id, "user_id": user_id},
                        output_snapshot={}, reasoning="Saved new payment token for autonomous charges"
                    )
        
        elif order_id:
            mandate = db.query(PaymentMandate).filter_by(razorpay_order_id=order_id).first()
            if mandate:
                reconcile_payment(db, mandate.mandate_id)
    except Exception as e:
        pass # Never fail the 200 OK webhook response
        
    return {"status": "ok"}
