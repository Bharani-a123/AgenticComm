import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
import json
from sqlalchemy import text

from app.main import app
from app.db.postgres import SessionLocal
from app.db.models import IntentMandate, CartMandate, Product, Merchant

client = TestClient(app)

def test_checkout_trust_boundary():
    db = SessionLocal()
    
    # 1. Setup mock data in DB
    user_id = 'test_user_trust'
    merchant_id = uuid4()
    db.execute(
        text("INSERT INTO merchants (merchant_id, name) VALUES (:mid, 'Test Merchant') ON CONFLICT DO NOTHING"),
        {'mid': merchant_id}
    )
    
    product_id = uuid4()
    db.execute(
        text("INSERT INTO products (product_id, merchant_id, merchant_sku, category, raw_attributes, price, currency) VALUES (:pid, :mid, 'sku123', 'laptop', '{}', 5000.0, 'INR') ON CONFLICT DO NOTHING"),
        {'pid': product_id, 'mid': merchant_id}
    )
    
    intent_id = uuid4()
    db.add(IntentMandate(
        mandate_id=intent_id,
        user_id=user_id,
        category='laptop',
        constraints={'budget_max': 1000.0},
        completeness=1.0
    ))
    db.flush()
    
    cart_id = uuid4()
    db.add(CartMandate(
        mandate_id=cart_id,
        intent_mandate_id=intent_id,
        product_id=product_id,
        price_at_selection=5000.0,
        payable_amount=5000.0
    ))
    db.commit()
    
    try:
        # 2. Simulate malicious client attempting to override the limits in the payload
        payload = {
            'cart_mandate_id': str(cart_id),
            'user_id': user_id,
            'current_autopay_limit': 99999.0,
            'current_mandate_limit': 99999.0
        }
        
        # 3. Post to /api/checkout
        res = client.post('/api/checkout', json=payload)
        assert res.status_code == 200
        
        data = res.json()
        
        # 4. Assert it rejected auto-payment because the true DB budget_max is 1000
        assert data['status'] == 'needs_confirmation'
        
    finally:
        # Cleanup
        db.execute(text('DELETE FROM cart_mandates WHERE mandate_id = :cid'), {'cid': cart_id})
        db.execute(text('DELETE FROM intent_mandates WHERE mandate_id = :iid'), {'iid': intent_id})
        db.execute(text('DELETE FROM products WHERE product_id = :pid'), {'pid': product_id})
        db.execute(text('DELETE FROM merchants WHERE merchant_id = :mid'), {'mid': merchant_id})
        db.commit()
        db.close()

