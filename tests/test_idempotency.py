import pytest
import uuid
from unittest.mock import patch
from sqlalchemy.exc import IntegrityError
from app.db.postgres import SessionLocal
from app.db.models import PaymentMandate as DBPaymentMandate, IntentMandate, CartMandate, Product, Merchant, Coupon
from app.protocols.ap2.mandates import PaymentMandate
from app.services.policy_engine import PolicyDecision
from app.services.payment_executor import execute_payment, PaymentExecutionError
from app.db.redis import get_redis

@pytest.fixture
def db():
    session = SessionLocal()
    session.query(DBPaymentMandate).delete()
    session.query(CartMandate).delete()
    session.query(IntentMandate).delete()
    session.query(Product).delete()
    session.query(Coupon).delete()
    session.query(Merchant).delete()
    session.commit()
    get_redis().flushall()
    yield session
    session.rollback()
    session.close()

def create_parents(db, cart_id):
    """Satisfies Postgres Foreign Key constraints for tests"""
    m = Merchant(merchant_id=uuid.uuid4(), name=f"Test_{uuid.uuid4()}")
    db.add(m)
    db.flush()
    p = Product(product_id=uuid.uuid4(), merchant_id=m.merchant_id, merchant_sku=f"sku_{uuid.uuid4()}", category="test", price=100, raw_attributes={})
    db.add(p)
    db.flush()
    i = IntentMandate(mandate_id=uuid.uuid4(), user_id="u", category="test", constraints={}, completeness=1.0)
    db.add(i)
    db.flush()
    c = CartMandate(mandate_id=cart_id, intent_mandate_id=i.mandate_id, product_id=p.product_id, price_at_selection=100, payable_amount=100)
    db.add(c)
    db.commit()

def test_idempotency_app_layer_guard(db):
    cart_id = uuid.uuid4()
    create_parents(db, cart_id)
    
    pm = PaymentMandate(
        mandate_id=uuid.uuid4(), cart_mandate_id=cart_id, amount=100.0,
        authorization_type="auto", idempotency_key="idem_123"
    )
    policy = PolicyDecision(approved=True, authorization_type="auto", reason="ok")
    
    with patch("app.services.payment_executor.create_order") as mock_create:
        mock_create.return_value = {"id": "order_123"}
        
        res1 = execute_payment(db, pm, policy)
        res2 = execute_payment(db, pm, policy)
        
        assert mock_create.call_count == 1
        assert res1.razorpay_order_id == "order_123"
        assert res2.razorpay_order_id == "order_123"

def test_db_unique_constraint(db):
    cart_id = uuid.uuid4()
    create_parents(db, cart_id)
    
    pm1 = DBPaymentMandate(
        mandate_id=uuid.uuid4(), cart_mandate_id=cart_id, amount=100.0,
        authorization_type="auto", status="pending", idempotency_key="idem_abc"
    )
    pm2 = DBPaymentMandate(
        mandate_id=uuid.uuid4(), cart_mandate_id=cart_id, amount=200.0,
        authorization_type="auto", status="pending", idempotency_key="idem_abc"
    )
    db.add(pm1)
    db.commit()
    
    db.add(pm2)
    with pytest.raises(IntegrityError):
        db.commit()

def test_unapproved_policy_raises(db):
    cart_id = uuid.uuid4()
    create_parents(db, cart_id)
    
    pm = PaymentMandate(
        mandate_id=uuid.uuid4(), cart_mandate_id=cart_id, amount=100.0,
        authorization_type="user_confirmed", idempotency_key="idem_reject"
    )
    policy = PolicyDecision(approved=False, authorization_type="user_confirmed", reason="no")
    
    with pytest.raises(PaymentExecutionError, match="Policy decision is NOT approved"):
        execute_payment(db, pm, policy)
