from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.postgres import get_db
from app.db.models import AuditLog, CartMandate, PaymentMandate
from app.services.audit_ledger import verify_chain_integrity
from typing import Optional
from uuid import UUID

router = APIRouter()

@router.get('/audit')
def get_audit_logs(reference_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(AuditLog)
    
    if reference_id:
        try:
            ref_uuid = UUID(reference_id)
            # Find related mandates
            intent_id = None
            cart_id = None
            payment_ids = []
            
            # 1. Could it be a Cart Mandate?
            cart = db.query(CartMandate).filter_by(mandate_id=ref_uuid).first()
            if cart:
                cart_id = cart.mandate_id
                intent_id = cart.intent_mandate_id
                payments = db.query(PaymentMandate).filter_by(cart_mandate_id=cart.mandate_id).all()
                payment_ids = [p.mandate_id for p in payments]
                
            # Gather all related IDs
            related_ids = [ref_uuid]
            if intent_id: related_ids.append(intent_id)
            if cart_id: related_ids.append(cart_id)
            related_ids.extend(payment_ids)
            
            # Filter logs where reference_id is in related_ids
            query = query.filter(AuditLog.reference_id.in_(related_ids))
        except ValueError:
            pass # Ignore invalid UUID
        
    logs = query.order_by(AuditLog.log_id.desc()).limit(100).all()
    is_valid, broken_id = verify_chain_integrity(db)
    
    return {
        'chain_valid': is_valid,
        'broken_log_id': broken_id,
        'logs': logs
    }
