import pytest
import uuid
from app.protocols.ap2.mandates import IntentMandate
from app.services.ranking_pre_filter import pre_filter_products

def test_pre_filter_products():
    intent = IntentMandate(
        mandate_id=uuid.uuid4(),
        user_id="user1",
        category="saree",
        constraints={"budget_max": 2500},
        autopay_limit=2500,
        completeness=1.0
    )
    
    products = [
        {"id": 1, "category": "saree", "price": 2000, "stock": True}, # Valid
        {"id": 2, "category": "saree", "price": 3000, "stock": True}, # Over-budget
        {"id": 3, "category": "saree", "price": 2000, "stock": False}, # Out of stock
        {"id": 4, "category": "chair", "price": 2000, "stock": True}, # Wrong category
        {"id": 5, "category": "saree", "price": 1500, "stock": True}, # Valid
    ]
    
    filtered = pre_filter_products(products, intent)
    assert len(filtered) == 2
    assert filtered[0]["id"] == 1
    assert filtered[1]["id"] == 5

def test_pre_filter_never_raises_on_empty_or_missing_budget():
    intent_no_budget = IntentMandate(
        mandate_id=uuid.uuid4(),
        user_id="user1",
        category="saree",
        constraints={}, # Missing budget constraint
        autopay_limit=2500,
        completeness=1.0
    )
    
    filtered = pre_filter_products([], intent_no_budget)
    assert filtered == []
    
    products = [{"id": 1, "category": "saree", "price": 999999, "stock": True}]
    filtered2 = pre_filter_products(products, intent_no_budget)
    # Budget missing means float('inf'), so price is fine. Stock true. Category matches.
    assert len(filtered2) == 1
    assert filtered2[0]["id"] == 1
