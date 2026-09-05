import pytest
import uuid
from app.db.postgres import SessionLocal
from app.db.models import AuditLog
from app.services.audit_ledger import write_audit_log, verify_chain_integrity

@pytest.fixture
def db():
    session = SessionLocal()
    # Clean up before test
    session.query(AuditLog).delete()
    session.commit()
    yield session
    # Clean up after test
    session.query(AuditLog).delete()
    session.commit()
    session.close()

def test_audit_chain_integrity_and_tampering(db):
    # 1. Write 5 sequential logs
    for i in range(5):
        write_audit_log(
            db=db,
            agent_name="TestAgent",
            event_type="test_event",
            reference_id=uuid.uuid4(),
            input_snapshot={"step": i},
            output_snapshot={"status": "ok"},
            reasoning=f"Reason {i}"
        )
    
    # 2. Verify chain is pristine
    is_valid, bad_id = verify_chain_integrity(db)
    assert is_valid is True
    assert bad_id is None
    
    # 3. Simulate Tampering (Update DB directly behind the application's back)
    logs = db.query(AuditLog).order_by(AuditLog.log_id.asc()).all()
    target_log = logs[2] # Tamper with the 3rd log
    
    # We mutate the JSON snapshot directly simulating a bad actor modifying the database
    # to cover their tracks.
    target_log.input_snapshot = {"step": 999}
    db.commit()
    
    # 4. Verify chain detects tampering
    is_valid, bad_id = verify_chain_integrity(db)
    assert is_valid is False
    assert bad_id == target_log.log_id # Identifies exactly which row broke the hash chain
