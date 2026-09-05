import hashlib
import json
from typing import Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models import AuditLog
from datetime import datetime

def write_audit_log(
    db: Session,
    agent_name: str,
    event_type: str,
    reference_id: Optional[UUID],
    input_snapshot: Optional[dict],
    output_snapshot: Optional[dict],
    reasoning: str,
) -> AuditLog:
    """
    Writes a new tamper-evident audit log entry.
    """
    # 1. Fetch curr_hash of the most recent row
    last_log = db.scalar(select(AuditLog).order_by(AuditLog.log_id.desc()).limit(1))
    prev_hash = last_log.curr_hash if last_log else "GENESIS"

    dt_now = datetime.utcnow().isoformat()
    
    # 2. Build canonical JSON
    payload = {
        "agent_name": agent_name,
        "event_type": event_type,
        "reference_id": str(reference_id) if reference_id else None,
        "input_snapshot": input_snapshot,
        "output_snapshot": output_snapshot,
        "reasoning": reasoning,
        "prev_hash": prev_hash,
        "timestamp": dt_now
    }
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    
    # 3. curr_hash = sha256(prev_hash + canonical_json)
    hash_input = prev_hash + canonical_json
    curr_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

    # 4. Insert new AuditLog row
    new_log = AuditLog(
        agent_name=agent_name,
        event_type=event_type,
        reference_id=reference_id,
        input_snapshot=input_snapshot,
        output_snapshot=output_snapshot,
        reasoning=reasoning,
        prev_hash=prev_hash,
        curr_hash=curr_hash,
        created_at=datetime.fromisoformat(dt_now)
    )
    db.add(new_log)
    
    # 5. Commit in the SAME transaction
    db.commit()
    db.refresh(new_log)
    return new_log

def verify_chain_integrity(db: Session) -> Tuple[bool, Optional[int]]:
    """
    Walks the entire audit_log table in order, recomputes each row's hash from its
    stored content + the previous row's curr_hash, and compares to the stored curr_hash.
    Returns (True, None) if the whole chain is valid.
    Returns (False, log_id) at the FIRST row where recomputed hash != stored hash.
    """
    logs = db.scalars(select(AuditLog).order_by(AuditLog.log_id.asc())).all()
    
    expected_prev = "GENESIS"
    for log in logs:
        if log.prev_hash != expected_prev:
            return False, log.log_id
            
        payload = {
            "agent_name": log.agent_name,
            "event_type": log.event_type,
            "reference_id": str(log.reference_id) if log.reference_id else None,
            "input_snapshot": log.input_snapshot,
            "output_snapshot": log.output_snapshot,
            "reasoning": log.reasoning,
            "prev_hash": log.prev_hash,
            "timestamp": log.created_at.isoformat()
        }
        canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        hash_input = log.prev_hash + canonical_json
        recomputed_curr = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
        
        if recomputed_curr != log.curr_hash:
            return False, log.log_id
            
        expected_prev = log.curr_hash
        
    return True, None
