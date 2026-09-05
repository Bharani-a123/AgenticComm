"""
Ranking Agent  (v2 — deterministic)
-------------------------------------
Replaces the old LLM-based ranker with:
  1. Budget relaxation  (coupon-aware, up to 130%)
  2. Deterministic 6-dimension scoring engine
  3. Checkout assembly  (CartMandate + PolicyDecision per product)
  4. Lightweight LLM explainer (~300 tokens — just "why these 5")
"""
import json
import logging
from app.agents.state import ConversationState
from app.agents.llm_client import call_llm
from app.db.postgres import SessionLocal
from app.services.budget_relaxation import relax_budget
from app.services.ranking_engine import rank_products
from app.services.checkout_assembler import assemble_checkout
from app.services.audit_ledger import write_audit_log

logger = logging.getLogger(__name__)


def run_ranking_agent(state: ConversationState) -> ConversationState:
    candidates = state.get("candidate_products", [])
    intent = state.get("intent_mandate")

    if not candidates or not intent:
        return state

    constraints = intent.constraints
    budget_max = constraints.get("budget_max", float("inf"))

    # ── 1. Budget relaxation ─────────────────────────────────────────────
    eligible, effective_budget = relax_budget(candidates, budget_max)

    out_of_budget_fallback = False
    if not eligible:
        out_of_budget_fallback = True
        # Sort ALL candidates by effective price and take the absolute cheapest, completely ignoring budget
        candidates.sort(key=lambda x: x.get("effective_price", x.get("price", float("inf"))))
        eligible = candidates[:5]
        min_found_price = eligible[0].get("effective_price", eligible[0].get("price", 0)) if eligible else 0
        effective_budget = 999999.0 # Use large float instead of inf to avoid PostgreSQL JSON syntax error
        
        if "messages" not in state:
            state["messages"] = []
        state["messages"].append({
            "role": "assistant",
            "content": (
                f"Sorry, no products are available at your ₹{budget_max:,.0f} budget (even with our standard 30% flexibility). "
                f"The minimum budget starts from ₹{min_found_price:,.0f}. I have provided the most affordable options we have below:"
            )
        })

    # ✨ 2. Deterministic ranking ✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨
    ranked = rank_products(
        eligible,
        constraints,
        budget_max if not out_of_budget_fallback else effective_budget,
        top_n=5,
        max_per_merchant=2,
    )

    # ── 3. Checkout assembly ─────────────────────────────────────────────
    db = SessionLocal()
    try:
        checkout_ready = assemble_checkout(db, ranked, intent)
    except Exception as e:
        logger.error("Checkout assembly failed: %s", e)
        checkout_ready = ranked  # degrade gracefully — still show products
    finally:
        db.close()

    # ── 4. LLM explainer (tiny payload) ──────────────────────────────────
    try:
        checkout_ready = _attach_explanations(checkout_ready, constraints, budget_max)
    except Exception as e:
        logger.warning("LLM explainer failed, using fallback: %s", e)
        _attach_fallback_explanations(checkout_ready)

    # ── 5. Update state ──────────────────────────────────────────────────
    state["candidate_products"] = checkout_ready

    if "messages" not in state:
        state["messages"] = []

    if not out_of_budget_fallback:
        budget_note = ""
        relaxed_count = sum(1 for p in checkout_ready if p.get("budget_relaxed"))
        if relaxed_count > 0:
            budget_note = (
                f" ({relaxed_count} are slightly above your ₹{budget_max:,.0f} budget "
                f"but included with coupons applied)"
            )

        state["messages"].append({
            "role": "assistant",
            "content": (
                f"Here are the top {len(checkout_ready)} picks for you{budget_note}. "
                "Each product is checkout-ready — just click to purchase!"
            ),
        })

    # Audit log
    db2 = SessionLocal()
    try:
        write_audit_log(
            db2, "ranking_agent", "ranked_deterministic",
            intent.mandate_id,
            {"total_eligible": len(eligible), "effective_budget": effective_budget},
            {
                "top_products": [
                    {"id": p.get("id"), "score": p.get("final_score"), "auth": p.get("payment_authorization")}
                    for p in checkout_ready
                ]
            },
            f"Deterministic ranking: {len(eligible)} eligible → top {len(checkout_ready)} "
            f"(budget: ₹{budget_max:.0f}, effective: ₹{effective_budget:.0f})",
        )
    finally:
        db2.close()

    return state


# ── LLM Explainer (tiny payload) ─────────────────────────────────────────

def _attach_explanations(products, constraints, budget_max):
    """
    Send ONLY a compact summary of the top 5 to the LLM.
    ~300 tokens total — well within any model's limit.
    """
    with open("app/agents/prompts/explainer.md") as f:
        prompt = f.read()

    # Build a slim payload — only what the LLM needs to write explanations
    slim = []
    for p in products:
        slim.append({
            "product_id": p.get("id"),
            "rank": p.get("rank"),
            "price": p.get("price"),
            "effective_price": p.get("effective_price"),
            "coupon_code": (p.get("applied_coupon") or {}).get("code"),
            "discount": (p.get("applied_coupon") or {}).get("discount_amount"),
            "rating": p.get("rating"),
            "ram_gb": p.get("ram_gb"),
            "storage_gb": p.get("storage_gb"),
            "camera_priority": p.get("camera_priority"),
            "budget_relaxed": p.get("budget_relaxed", False),
            "original_budget": p.get("original_budget"),
            "score_breakdown": p.get("score_breakdown"),
            "merchant_name": p.get("merchant_name"),
        })

    resp_str = call_llm(prompt, json.dumps(slim), json_mode=True)

    try:
        explanations = json.loads(resp_str)
    except (json.JSONDecodeError, TypeError):
        _attach_fallback_explanations(products)
        return products

    # Map explanations back to products
    explanation_map = {e.get("product_id"): e for e in explanations if isinstance(e, dict)}
    for p in products:
        mapped = explanation_map.get(p.get("id"))
        if mapped:
            p["explanation"] = mapped.get("explanation", _fallback_explanation(p))
        else:
            p["explanation"] = _fallback_explanation(p)
            
        p["product_title"] = p.get("product_name") or f"{p.get('merchant_name', 'Product')} {str(p.get('category', '')).title()}"

    return products


def _attach_fallback_explanations(products):
    """Deterministic fallback if LLM is unavailable."""
    for p in products:
        p["explanation"] = _fallback_explanation(p)


def _fallback_explanation(p):
    """Generate a simple explanation without LLM."""
    parts = []
    if p.get("ram_gb"):
        parts.append(f"{p['ram_gb']}GB RAM")
    if p.get("storage_gb"):
        parts.append(f"{p['storage_gb']}GB storage")
    if p.get("camera_priority"):
        parts.append("camera-focused")

    specs = ", ".join(parts)
    price_str = f"₹{p.get('effective_price', p.get('price', 0)):,.0f}"

    coupon = p.get("applied_coupon")
    if coupon:
        price_str += f" (save ₹{coupon.get('discount_amount', 0):,.0f} with {coupon.get('code', '')})"

    if p.get("budget_relaxed"):
        return f"Slightly over budget but great value — {specs} at {price_str}. Rating: {p.get('rating', 'N/A')}★"

    return f"{specs} at {price_str}. Rating: {p.get('rating', 'N/A')}★"
