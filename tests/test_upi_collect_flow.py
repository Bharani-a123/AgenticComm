import pytest
from unittest.mock import patch, MagicMock
import uuid
from sqlalchemy.orm import Session
from app.protocols.ap2.mandates import PaymentMandate
from app.services.policy_engine import PolicyDecision
from app.services.payment_executor import execute_payment, PaymentExecutionError

@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)

@pytest.fixture
def mock_payment_mandate():
    return PaymentMandate(
        mandate_id=uuid.uuid4(),
        cart_mandate_id=uuid.uuid4(),
        amount=100.0,
        authorization_type='auto',
        idempotency_key='deterministic_key_123'
    )

@pytest.fixture
def policy_approved():
    return PolicyDecision(approved=True, authorization_type='auto', reason='Looks good')

def setup_db_mock(mock_db):
    def mock_query(model):
        query_mock = MagicMock()
        def mock_filter_by(**kwargs):
            filter_mock = MagicMock()
            if model.__name__ == 'PaymentMandate':
                filter_mock.first.return_value = None
            elif model.__name__ == 'CartMandate':
                cart_mock = MagicMock()
                cart_mock.intent_mandate_id = 'intent_123'
                filter_mock.first.return_value = cart_mock
            elif model.__name__ == 'IntentMandate':
                intent_mock = MagicMock()
                intent_mock.user_id = 'user_123'
                filter_mock.first.return_value = intent_mock
            return filter_mock
        query_mock.filter_by = mock_filter_by
        return query_mock
    mock_db.query = mock_query

@patch('app.services.payment_executor.write_audit_log')
@patch('app.services.payment_executor.execute_tool_call')
@patch('app.services.payment_executor.get_redis')
@patch('app.services.payment_executor.decrement_stock_atomic')
@patch('app.services.payment_executor.get_product_id_for_cart')
@patch('app.mcp.razorpay_client.create_upi_collect_payment')
def test_upi_collect_payment_chain_success(mock_upi_collect, mock_get_product, mock_decrement_stock, mock_get_redis, mock_execute_tool_call, mock_write_audit_log, mock_db, mock_payment_mandate, policy_approved):
    redis_mock = MagicMock()
    redis_mock.set.return_value = True
    redis_mock.hgetall.return_value = None
    mock_get_redis.return_value = redis_mock
    
    setup_db_mock(mock_db)

    mock_execute_tool_call.side_effect = [{'id': 'order_123'}]
    mock_upi_collect.return_value = {
        'razorpay_payment_id': 'pay_upi123',
        'next': [{'action': 'poll', 'url': 'http://mock-poll.com'}]
    }
    
    with patch('requests.get') as mock_get:
        poll_res = MagicMock()
        poll_res.status_code = 200
        poll_res.json.return_value = {'status': 'captured'}
        mock_get.return_value = poll_res
        
        mock_decrement_stock.return_value = True

        result = execute_payment(mock_db, mock_payment_mandate, policy_approved)

        assert result.status == 'captured'
        assert result.razorpay_order_id == 'order_123'
        mock_upi_collect.assert_called_once()
        mock_decrement_stock.assert_called_once()
