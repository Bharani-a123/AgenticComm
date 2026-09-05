import pytest
import threading
from app.db.models import Merchant, Product
from app.db.postgres import SessionLocal
from app.services.order_service import decrement_stock_atomic

@pytest.fixture
def setup_stock():
    db = SessionLocal()
    try:
        from app.db.models import PaymentMandate, CartMandate
        db.query(PaymentMandate).delete()
        db.query(CartMandate).delete()
        db.query(Product).delete()
        db.query(Merchant).delete()
        
        m = Merchant(name="Stock Merchant")
        db.add(m)
        db.commit()
        db.refresh(m)
        
        p = Product(
            merchant_id=m.merchant_id,
            merchant_sku="TEST-SKU",
            category="saree",
            raw_attributes={},
            normalized={},
            price=100.0,
            stock=True
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        
        yield p.product_id
    finally:
        db.close()

def test_atomic_stock_decrement(setup_stock):
    product_id = setup_stock
    
    # We will simulate concurrent decrement by just running it twice in a row.
    # The first should return True (won the stock), the second False (already taken).
    db1 = SessionLocal()
    db2 = SessionLocal()
    
    try:
        success1 = decrement_stock_atomic(db1, product_id)
        success2 = decrement_stock_atomic(db2, product_id)
        
        assert success1 is True, "First attempt should win the stock"
        assert success2 is False, "Second attempt should fail as stock is already False"
        
        # Verify DB state
        p = db1.query(Product).filter_by(product_id=product_id).first()
        assert p.stock is False
    finally:
        db1.close()
        db2.close()
