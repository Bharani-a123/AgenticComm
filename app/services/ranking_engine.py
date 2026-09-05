"""
Deterministic Ranking Engine
------------------------------
Scores every product across 6 dimensions, picks the top‑N with
merchant diversity, and returns fully scored + ranked results.
NO LLM is used here — pure math.
"""
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# ── Weight configuration ─────────────────────────────────────────────────
WEIGHTS = {
    "constraint_match": 0.35,
    "value":            0.20,  # Reduced from 0.25 to prevent tiny price diffs from overriding quality
    "rating":           0.20,  # Increased from 0.15 to heavily penalize low quality
    "coupon_savings":   0.10,
    "spec_headroom":    0.10,
    "delivery":         0.05,
}

# Simulated delivery days per merchant (configurable)
MERCHANT_DELIVERY_DAYS: Dict[str, int] = {
    "Merchant A": 3,
    "Merchant B": 5,
    "Merchant C": 2,
}
DEFAULT_DELIVERY_DAYS = 4


# ── Individual scoring functions ─────────────────────────────────────────

def _constraint_match_score(product: Dict[str, Any], constraints: Dict[str, Any]) -> float:
    """
    How well the product's specs match the user's requested constraints.
    Skips 'budget_max' (handled by value_score).
    """
    spec_keys = [k for k in constraints if k != "budget_max"]
    if not spec_keys:
        return 1.0

    total = 0.0
    for key in spec_keys:
        user_val = constraints[key]
        prod_val = product.get(key)

        if prod_val is None:
            total += 0.0
            continue

        # Boolean constraints (e.g. camera_priority)
        if isinstance(user_val, bool) or key == "camera_priority":
            user_bool = _to_bool(user_val)
            prod_bool = _to_bool(prod_val)
            if not user_bool:
                # User doesn't care → any product is fine
                total += 1.0
            elif prod_bool:
                total += 1.0
            else:
                total += 0.3
            continue

        # Numeric constraints (e.g. ram_gb, storage_gb)
        try:
            user_num = float(user_val)
            prod_num = float(prod_val)
        except (ValueError, TypeError):
            # String match fallback
            total += 1.0 if str(user_val).lower() == str(prod_val).lower() else 0.0
            continue

        if prod_num == user_num:
            total += 1.0        # exact match
        elif prod_num > user_num:
            total += 0.8        # over‑spec (still good)
        else:
            total += 0.0        # under‑spec (bad)

    return total / len(spec_keys)


def _value_score(product: Dict[str, Any], budget_max: float) -> float:
    """Lower effective_price relative to budget = better value."""
    if budget_max <= 0:
        return 0.0
    eff = product.get("effective_price", product.get("price", 0))
    score = 1.0 - (eff / budget_max)
    return max(0.0, min(1.0, score))


def _rating_score(product: Dict[str, Any]) -> float:
    """Normalize rating (3.0–5.0) → 0.0–1.0."""
    rating = product.get("rating")
    if rating is None:
        return 0.0
    score = (float(rating) - 3.0) / 2.0
    return max(0.0, min(1.0, score))


def _coupon_savings_score(product: Dict[str, Any]) -> float:
    """Bonus for products with an applicable coupon discount."""
    coupon = product.get("applied_coupon")
    if not coupon:
        return 0.0
    price = product.get("price", 0)
    if price <= 0:
        return 0.0
    discount = coupon.get("discount_amount", 0)
    ratio = discount / price
    return min(ratio * 5.0, 1.0)


def _spec_headroom_score(product: Dict[str, Any], constraints: Dict[str, Any]) -> float:
    """Bonus for exceeding minimum requirements or having good warranty."""
    headroom = 0.0
    count = 0

    for key in ("ram_gb", "storage_gb"):
        user_val = constraints.get(key)
        prod_val = product.get(key)
        if user_val is not None and prod_val is not None:
            try:
                if float(prod_val) > float(user_val):
                    headroom += 0.5
            except (ValueError, TypeError):
                pass
            count += 1

    # Bonus for warranty (up to 3 years)
    warranty = product.get("warranty_years")
    if warranty is not None:
        try:
            headroom += min(float(warranty) / 3.0, 1.0)
            count += 1
        except (ValueError, TypeError):
            pass

    return min(headroom, 1.0) if count > 0 else 0.0


def _delivery_score(product: Dict[str, Any]) -> float:
    """Simulated delivery speed score based on merchant."""
    merchant_id = product.get("merchant_id", "")
    # Try to use merchant name if available, else use merchant_id for lookup
    merchant_name = product.get("merchant_name", "")
    days = MERCHANT_DELIVERY_DAYS.get(merchant_name, DEFAULT_DELIVERY_DAYS)
    score = 1.0 - (days / 7.0)
    return max(0.0, min(1.0, score))


# ── Composite scorer ─────────────────────────────────────────────────────

def score_product(
    product: Dict[str, Any],
    constraints: Dict[str, Any],
    budget_max: float,
) -> Tuple[float, Dict[str, float]]:
    """
    Returns (final_score, breakdown_dict).
    """
    breakdown = {
        "constraint_match": round(_constraint_match_score(product, constraints), 4),
        "value":            round(_value_score(product, budget_max), 4),
        "rating":           round(_rating_score(product), 4),
        "coupon_savings":   round(_coupon_savings_score(product), 4),
        "spec_headroom":    round(_spec_headroom_score(product, constraints), 4),
        "delivery":         round(_delivery_score(product), 4),
    }

    final = sum(WEIGHTS[k] * breakdown[k] for k in WEIGHTS)
    return round(final, 4), breakdown


# ── Top‑N selection with merchant diversity ──────────────────────────────

def rank_products(
    products: List[Dict[str, Any]],
    constraints: Dict[str, Any],
    budget_max: float,
    top_n: int = 5,
    max_per_merchant: int = 2,
) -> List[Dict[str, Any]]:
    """
    Score → sort → enforce merchant diversity → return top_n.
    Each product in the result is enriched with:
      rank, final_score, score_breakdown
    """
    if not products:
        return []

    scored: List[Tuple[Dict[str, Any], float, Dict[str, float]]] = []
    for p in products:
        final, breakdown = score_product(p, constraints, budget_max)
        scored.append((p, final, breakdown))

    # Sort descending by score
    scored.sort(key=lambda x: x[1], reverse=True)

    # Merchant diversity: max `max_per_merchant` per merchant
    merchant_count: Dict[str, int] = {}
    result: List[Dict[str, Any]] = []

    for product, final, breakdown in scored:
        mid = product.get("merchant_id", "unknown")
        if merchant_count.get(mid, 0) >= max_per_merchant:
            continue

        merchant_count[mid] = merchant_count.get(mid, 0) + 1
        product["rank"] = len(result) + 1
        product["final_score"] = final
        product["score_breakdown"] = breakdown
        result.append(product)

        if len(result) >= top_n:
            break

    logger.info(
        "Ranking engine: %d products scored → top %d selected "
        "(merchants: %s)",
        len(products), len(result),
        {k: v for k, v in merchant_count.items()},
    )
    return result


# ── Helpers ──────────────────────────────────────────────────────────────

def _to_bool(val) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val > 0
    if isinstance(val, str):
        return val.lower() in ("true", "yes", "1")
    return False
