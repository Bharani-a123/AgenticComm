"""
Budget Relaxation Service
--------------------------
When the user's exact budget yields fewer than `min_results` products, we
progressively expand the ceiling in 10% increments up to 130% of the
original budget.  Coupons are already applied (effective_price) BEFORE this
runs, so a ₹12 000 product with a FLAT500 coupon is evaluated at ₹11 500.
"""
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# 1.0 → exact, then 10% steps up to 130%
RELAXATION_MULTIPLIERS = [1.0, 1.1, 1.2, 1.3]
MIN_RESULTS_DEFAULT = 3


def relax_budget(
    products: List[Dict[str, Any]],
    budget_max: float,
    min_results: int = MIN_RESULTS_DEFAULT,
) -> Tuple[List[Dict[str, Any]], float]:
    """
    Returns (eligible_products, effective_budget_used).

    Each product is tagged:
      budget_relaxed  : bool   – True if this product only became eligible
                                  because the budget was expanded.
      original_budget : float  – the user's stated budget.
      relaxed_budget  : float  – the ceiling actually used (may == original).
    """
    for multiplier in RELAXATION_MULTIPLIERS:
        threshold = round(budget_max * multiplier, 2)
        eligible = _filter_by_threshold(products, threshold)

        if len(eligible) >= min_results:
            _tag_products(eligible, budget_max, threshold)
            logger.info(
                "Budget relaxation: multiplier=%.1fx  threshold=%.2f  "
                "eligible=%d  (original_budget=%.2f)",
                multiplier, threshold, len(eligible), budget_max,
            )
            return eligible, threshold

    # Even at 130% we may have fewer than min_results – return whatever we have
    threshold = round(budget_max * RELAXATION_MULTIPLIERS[-1], 2)
    eligible = _filter_by_threshold(products, threshold)
    _tag_products(eligible, budget_max, threshold)

    logger.info(
        "Budget relaxation exhausted at 130%%: threshold=%.2f  eligible=%d",
        threshold, len(eligible),
    )
    return eligible, threshold


# ── helpers ──────────────────────────────────────────────────────────────

def _effective_price(product: Dict[str, Any]) -> float:
    return product.get("effective_price", product.get("price", 0))


def _filter_by_threshold(
    products: List[Dict[str, Any]], threshold: float
) -> List[Dict[str, Any]]:
    return [p for p in products if _effective_price(p) <= threshold]


def _tag_products(
    products: List[Dict[str, Any]],
    original_budget: float,
    threshold: float,
) -> None:
    for p in products:
        over_original = _effective_price(p) > original_budget
        p["budget_relaxed"] = over_original
        p["original_budget"] = original_budget
        p["relaxed_budget"] = threshold
