import pytest
import uuid
from unittest.mock import MagicMock
from app.protocols.ap2.mandates import IntentMandate, CartMandate
from app.services.policy_engine import evaluate_payment_authorization, confirm_user_authorization

def make_intent(limit: float) -> IntentMandate:
    return IntentMandate(
        mandate_id=uuid.uuid4(),
        user_id='user1',
        category='saree',
        constraints={},
        autopay_limit=limit,
        completeness=1.0
    )

def make_cart(amount: float) -> CartMandate:
    return CartMandate(
        mandate_id=uuid.uuid4(),
        intent_mandate_id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        price_at_selection=amount,
        payable_amount=amount
    )

def test_amount_below_autopay_limit():
    mock_db = MagicMock()
    mock_db.query.return_value.filter_by.return_value.first.return_value.category = 'saree'
    decision = evaluate_payment_authorization(mock_db, make_intent(2500), make_cart(2000))
    assert decision.approved is True
    assert decision.authorization_type == 'auto'

def test_amount_above_autopay_limit():
    mock_db = MagicMock()
    mock_db.query.return_value.filter_by.return_value.first.return_value.category = 'saree'
    decision = evaluate_payment_authorization(mock_db, make_intent(2500), make_cart(3000))
    assert decision.approved is False
    assert decision.authorization_type == 'user_confirmed'

def test_confirm_user_authorization_true():
    mock_db = MagicMock()
    mock_db.query.return_value.filter_by.return_value.first.return_value.category = 'saree'
    decision = evaluate_payment_authorization(mock_db, make_intent(2500), make_cart(3000))
    final = confirm_user_authorization(decision, True)
    assert final.approved is True
    assert final.authorization_type == 'user_confirmed'

def test_confirm_user_authorization_false():
    mock_db = MagicMock()
    mock_db.query.return_value.filter_by.return_value.first.return_value.category = 'saree'
    decision = evaluate_payment_authorization(mock_db, make_intent(2500), make_cart(3000))
    final = confirm_user_authorization(decision, False)
    assert final.approved is False
    assert final.authorization_type == 'rejected'

def test_amount_zero_or_negative():
    mock_db = MagicMock()
    mock_db.query.return_value.filter_by.return_value.first.return_value.category = 'saree'
    decision = evaluate_payment_authorization(mock_db, make_intent(2500), make_cart(0))
    assert decision.approved is False
    assert decision.authorization_type == 'rejected'
    
def test_llm_cannot_bypass_policy_engine():
    mock_db = MagicMock()
    mock_db.query.return_value.filter_by.return_value.first.return_value.category = 'saree'
    cart = make_cart(9999999)
    intent = make_intent(2500)
    decision = evaluate_payment_authorization(mock_db, intent, cart)
    assert decision.approved is False
    assert decision.authorization_type == 'user_confirmed'

