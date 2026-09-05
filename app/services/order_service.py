import logging
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

def decrement_stock_atomic(db: Session, product_id) -> bool:
    """
    Atomically marks a product out of stock ONLY if it was still in stock.
    Returns True if this call actually performed the update.
    """
    from app.db.models import Product
    from sqlalchemy import update

    result = db.execute(
        update(Product)
        .where(Product.product_id == product_id, Product.stock == True)
        .values(stock=False)
    )
    db.commit()
    return result.rowcount > 0

def get_product_id_for_cart(db: Session, cart_mandate_id):
    from app.db.models import CartMandate
    cart_mandate = db.query(CartMandate).filter_by(mandate_id=cart_mandate_id).first()
    return cart_mandate.product_id if cart_mandate else None

def create_order_from_mandate(db: Session, cart_mandate_id, payment_mandate_id) -> bool:
    """
    Simulates order creation on success path.
    Decrements stock.
    """
    from app.db.models import CartMandate
    cart_mandate = db.query(CartMandate).filter_by(mandate_id=cart_mandate_id).first()
    if cart_mandate:
        success = decrement_stock_atomic(db, cart_mandate.product_id)
        if not success:
            logger.warning(f"Oversell detected for product {cart_mandate.product_id}")
            return False
        return True
    return False
