from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from app.db.postgres import SessionLocal
from app.db.models import Product, Merchant, Coupon
import logging

logger = logging.getLogger(__name__)

def fetch_merchant_catalog(merchant_id, category: str) -> list[dict]:
    """One 'ACP call' to one merchant's catalog for a given category.
    Runs in its own DB session so it's safe to call from a worker thread."""
    db = SessionLocal()
    try:
        products = db.query(Product).filter(
            Product.merchant_id == merchant_id,
            Product.category == category,
        ).all()
        results = []
        for p in products:
            d = dict(p.normalized) if p.normalized else dict(p.raw_attributes)
            d["id"] = str(p.product_id)
            d["category"] = p.category
            d["merchant_id"] = str(p.merchant_id)
            d["price"] = float(p.price)
            d["stock"] = p.stock
            d["rating"] = float(p.rating) if p.rating else None
            results.append(d)
        return results
    finally:
        db.close()

def discover_products(category: str) -> list[dict]:
    """The real 'ACP Adapter': fans out to every merchant CONCURRENTLY, one thread
    per merchant, and aggregates. One merchant failing does not take down discovery
    for the others."""
    db = SessionLocal()
    try:
        merchants = db.query(Merchant).all()
    finally:
        db.close()

    all_products = []
    with ThreadPoolExecutor(max_workers=max(len(merchants), 1)) as executor:
        futures = {
            executor.submit(fetch_merchant_catalog, m.merchant_id, category): m.name
            for m in merchants
        }
        for future in as_completed(futures):
            merchant_name = futures[future]
            try:
                all_products.extend(future.result())
            except Exception as e:
                logger.warning(f"ACP fetch failed for merchant {merchant_name}: {e}")
    return all_products

def get_best_coupon_for_product(product: dict) -> dict | None:
    """
    Finds the single best applicable, active, non-expired coupon for this product
    from ITS merchant, respecting min_order_value and category applicability.
    Returns None if no coupon applies. Pure deterministic logic -- no LLM.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        coupons = db.query(Coupon).filter(
            Coupon.merchant_id == product["merchant_id"],
            Coupon.active == True,
            Coupon.valid_until >= now,
        ).all()

        price = product["price"]
        best = None
        best_discount_amount = 0.0

        for c in coupons:
            if c.applicable_category and c.applicable_category != product.get("category"):
                continue
            if price < float(c.min_order_value or 0):
                continue

            if c.discount_type == "flat":
                discount_amount = float(c.discount_value)
            else:  # percentage
                discount_amount = price * (float(c.discount_value) / 100.0)
                if c.max_discount_cap is not None:
                    discount_amount = min(discount_amount, float(c.max_discount_cap))

            discount_amount = min(discount_amount, price)  # never discount below 0

            if discount_amount > best_discount_amount:
                best_discount_amount = discount_amount
                best = {
                    "coupon_id": str(c.coupon_id),
                    "code": c.code,
                    "discount_amount": round(discount_amount, 2),
                    "effective_price": round(price - discount_amount, 2),
                }
        return best
    finally:
        db.close()

def attach_effective_pricing(products: list[dict]) -> list[dict]:
    """
    For every product, compute its best available coupon and effective_price.
    If no coupon applies, effective_price == price. This is what ranking and
    pre-filter should use for "is this within budget" and "is this the best deal" --
    not the raw sticker price alone.
    """
    for p in products:
        best_coupon = get_best_coupon_for_product(p)
        if best_coupon:
            p["applied_coupon"] = best_coupon
            p["effective_price"] = best_coupon["effective_price"]
        else:
            p["applied_coupon"] = None
            p["effective_price"] = p["price"]
    return products
