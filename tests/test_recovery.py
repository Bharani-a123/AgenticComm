import pytest
import uuid
import hmac
import hashlib
from unittest.mock import patch
from app.db.postgres import SessionLocal
from app.db.models import PaymentMandate as DBPaymentMandate, IntentMandate, CartMandate, Product, Merchant, Coupon
from app.services.recovery_service import handle_cancellation
from app.services.transaction_verifier import reconcile_payment
from app.mcp.razorpay_client import RazorpayClientError
from app.services.webhook_verifier import verify_webhook_signature
from app.core.config import get_settings

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
    yield session
    session.rollback()
    session.close()

def create_parents(db, cart_id):
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

@pytest.fixture
def mandate(db):
    cart_id = uuid.uuid4()
    create_parents(db, cart_id)
    m = DBPaymentMandate(
        mandate_id=uuid.uuid4(), cart_mandate_id=cart_id, amount=100.0,
        authorization_type="auto", status="pending", razorpay_order_id="order_test",
        idempotency_key="idem_test"
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m

def test_reconcile_payment_captured(db, mandate):
    with patch("app.services.recovery_service.fetch_payment_status") as mock_fetch:
        mock_fetch.return_value = {"status": "captured"}
        result = reconcile_payment(db, mandate.mandate_id)
        
        assert result.status == "captured"
        assert result.action_taken == "updated_to_captured"
        db.refresh(mandate)
        assert mandate.status == "captured"

def test_reconcile_payment_failed(db, mandate):
    with patch("app.services.recovery_service.fetch_payment_status") as mock_fetch:
        mock_fetch.return_value = {"status": "failed"}
        result = reconcile_payment(db, mandate.mandate_id)
        
        assert result.status == "failed"
        assert result.action_taken == "updated_to_failed"
        db.refresh(mandate)
        assert mandate.status == "failed"

def test_handle_cancellation_success(db, mandate):
    mandate.status = "captured"
    db.commit()
    with patch("app.services.recovery_service.refund_payment") as mock_refund:
        mock_refund.return_value = {"id": "rfnd_123"}
        result = handle_cancellation(db, mandate.mandate_id, "User requested cancel")
        
        assert result.status == "refunded"
        assert result.refund_id == "rfnd_123"
        db.refresh(mandate)
        assert mandate.status == "refunded"

def test_handle_cancellation_api_failure(db, mandate):
    mandate.status = "captured"
    db.commit()
    with patch("app.services.recovery_service.refund_payment") as mock_refund:
        mock_refund.side_effect = RazorpayClientError("Network error")
        with pytest.raises(RazorpayClientError):
            handle_cancellation(db, mandate.mandate_id, "User requested cancel")
            
        db.refresh(mandate)
        assert mandate.status == "captured"

def test_webhook_verifier():
    settings = get_settings()
    secret = settings.razorpay_webhook_secret.get_secret_value().encode("utf-8")
    payload = b'{"event":"payment.captured"}'
    valid_sig = hmac.new(key=secret, msg=payload, digestmod=hashlib.sha256).hexdigest()
    
    assert verify_webhook_signature(payload, valid_sig) is True
    assert verify_webhook_signature(payload, "invalid_sig") is False
    assert verify_webhook_signature(b'{"event":"payment.failed"}', valid_sig) is False
