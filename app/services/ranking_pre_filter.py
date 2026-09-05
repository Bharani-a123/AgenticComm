from typing import List, Dict, Any
from app.protocols.ap2.mandates import IntentMandate
import logging

logger = logging.getLogger(__name__)

def pre_filter_products(products: List[Dict[str, Any]], intent_mandate: IntentMandate) -> List[Dict[str, Any]]:
    """
    Deterministic hard-filter BEFORE the ranking engine scores anything:
      - products where stock == False
      - products not matching intent_mandate.category

    NOTE: Budget filtering is intentionally NOT done here.  It is handled by
    the ranking engine's budget_relaxation module, which progressively
    expands the ceiling (up to 130%) and applies coupons first — so a
    product that looks over-budget at sticker price may actually be within
    reach after a coupon.
    """
    filtered = []
    target_category = intent_mandate.category

    dropped_count = 0
    for product in products:
        if not product.get("stock", True):
            dropped_count += 1
            continue

        if target_category and product.get("category") != target_category:
            dropped_count += 1
            continue

        filtered.append(product)

    if dropped_count > 0:
        logger.info(f"Pre-filter dropped {dropped_count} ineligible products (out-of-stock / wrong-category).")

    return filtered
