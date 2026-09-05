import pytest
from unittest.mock import patch, MagicMock
import uuid
from datetime import datetime

from sqlalchemy.orm import Session
from app.db.models import PaymentMandate as DBPaymentMandate
from app.protocols.ap2.mandates import PaymentMandate
from app.services.policy_engine import PolicyDecision
from app.services.payment_executor import execute_payment, PaymentExecutionError

@pytest.fixture
def mock_db():
    db = MagicMock(spec=Session)
    return db

@pytest.fixture
def mock_payment_mandate():
    return PaymentMandate(
        mandate_id=uuid.uuid4(),
        cart_mandate_id=uuid.uuid4(),
        amount=100.0,
        authorization_type="auto",
        idempotency_key="deterministic_key_123"
    )

@pytest.fixture
def policy_approved():
    return PolicyDecision(approved=True, authorization_type="auto", reason="Looks good")

def setup_db_mock(mock_db, has_token=True):
    def mock_query(model):
        query_mock = MagicMock()
        def mock_filter_by(**kwargs):
            filter_mock = MagicMock()
            if model.__name__ == 'PaymentMandate':
                filter_mock.first.return_value = None
            elif model.__name__ == 'CartMandate':
                cart_mock = MagicMock()
                cart_mock.intent_mandate_id = "intent_123"
                filter_mock.first.return_value = cart_mock
            elif model.__name__ == 'IntentMandate':
                intent_mock = MagicMock()
                intent_mock.user_id = "user_123"
                filter_mock.first.return_value = intent_mock
            elif model.__name__ == 'PaymentToken':
                if has_token:
                    token_mock = MagicMock()
                    token_mock.razorpay_customer_id = "cust_123"
                    token_mock.razorpay_token_id = "token_123"
                    filter_mock.first.return_value = token_mock
                else:
                    filter_mock.first.return_value = None
            return filter_mock
        query_mock.filter_by = mock_filter_by
        return query_mock
    mock_db.query = mock_query

@patch("app.services.payment_executor.write_audit_log")
@patch("app.services.payment_executor.execute_tool_call")
@patch("app.services.payment_executor.get_redis")
@patch("app.services.payment_executor.decrement_stock_atomic")
@patch("app.services.payment_executor.get_product_id_for_cart")
@patch("app.mcp.razorpay_client.charge_saved_token")
def test_automatic_payment_chain_success(mock_charge, mock_get_product, mock_decrement_stock, mock_get_redis, mock_execute_tool_call, mock_write_audit_log, mock_db, mock_payment_mandate, policy_approved):
    redis_mock = MagicMock()
    redis_mock.set.return_value = True
    redis_mock.hgetall.return_value = None
    mock_get_redis.return_value = redis_mock
    
    setup_db_mock(mock_db)

    mock_execute_tool_call.side_effect = [{"id": "order_123"}]
    mock_charge.return_value = {"id": "pay_123"}
    mock_decrement_stock.return_value = True

    result = execute_payment(mock_db, mock_payment_mandate, policy_approved)

    assert result.status == "captured"
    assert result.razorpay_order_id == "order_123"
    mock_charge.assert_called_once()
    mock_decrement_stock.assert_called_once()

@patch("app.services.payment_executor.write_audit_log")
@patch("app.services.payment_executor.execute_tool_call")
@patch("app.services.payment_executor.get_redis")
@patch("app.services.payment_executor.reconcile_payment")
@patch("app.mcp.razorpay_client.charge_saved_token")
def test_automatic_payment_chain_recovery_on_capture_fail(mock_charge, mock_reconcile, mock_get_redis, mock_execute_tool_call, mock_write_audit_log, mock_db, mock_payment_mandate, policy_approved):
    redis_mock = MagicMock()
    redis_mock.set.return_value = True
    mock_get_redis.return_value = redis_mock
    setup_db_mock(mock_db)

    mock_execute_tool_call.side_effect = [{"id": "order_123"}]
    mock_charge.side_effect = Exception("Capture failed")

    with pytest.raises(PaymentExecutionError):
        execute_payment(mock_db, mock_payment_mandate, policy_approved)

    mock_reconcile.assert_called_once_with(mock_db, mock_payment_mandate.mandate_id)

@patch("app.services.payment_executor.write_audit_log")
@patch("app.services.payment_executor.execute_tool_call")
@patch("app.services.payment_executor.get_redis")
@patch("app.services.payment_executor.decrement_stock_atomic")
@patch("app.services.payment_executor.get_product_id_for_cart")
@patch("app.services.payment_executor.auto_refund_on_oversell")
@patch("app.mcp.razorpay_client.charge_saved_token")
def test_automatic_payment_chain_auto_refund(mock_charge, mock_auto_refund, mock_get_product, mock_decrement_stock, mock_get_redis, mock_execute_tool_call, mock_write_audit_log, mock_db, mock_payment_mandate, policy_approved):
    redis_mock = MagicMock()
    redis_mock.set.return_value = True
    mock_get_redis.return_value = redis_mock
    setup_db_mock(mock_db)

    mock_execute_tool_call.side_effect = [{"id": "order_123"}]
    mock_charge.return_value = {"id": "pay_123"}
    mock_decrement_stock.return_value = False

    with pytest.raises(PaymentExecutionError, match="Item oversold"):
        execute_payment(mock_db, mock_payment_mandate, policy_approved)

    mock_auto_refund.assert_called_once()
