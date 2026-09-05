"""
Checkout Assembler
-------------------
Takes ranked products + IntentMandate and pre-computes the FULL checkout
state for each product:
  • CartMandate   → persisted to DB
  • PolicyDecision → auto / user_confirmed / rejected
  • Merchant name  → resolved for display

When the frontend receives these products they are "checkout-ready":
one click triggers payment with no additional computation.
"""
import logging
import uuid
from typing import List, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import (
    CartMandate as DBCartMandate,
    IntentMandate as DBIntentMandate,
    Merchant,
)
from app.protocols.ap2.mandates import IntentMandate, CartMandate
from app.services.policy_engine import evaluate_payment_authorization
from app.services.audit_ledger import write_audit_log

logger = logging.getLogger(__name__)


def assemble_checkout(
    db: Session,
    products: List[Dict[str, Any]],
    intent_mandate: IntentMandate,
) -> List[Dict[str, Any]]:
    """
    For each ranked product:
      1. Persist IntentMandate to DB (idempotent).
      2. Create + persist a CartMandate.
      3. Evaluate PolicyDecision (auto / user_confirmed / rejected).
      4. Enrich the product dict with checkout metadata.
    Returns the same list, enriched in-place.
    """
    # ── 1. Persist IntentMandate (upsert) ────────────────────────────────
    _persist_intent_mandate(db, intent_mandate)

    # ── 2. Resolve merchant names (one query, cached for the batch) ──────
    merchant_names = _load_merchant_names(db)

    # ── 3. Assemble each product ─────────────────────────────────────────
    for product in products:
        try:
            product_id = UUID(product["id"])
            coupon_id = (
                UUID(product["applied_coupon"]["coupon_id"])
                if product.get("applied_coupon")
                else None
            )
            payable = product.get("effective_price", product.get("price", 0))

            # Create CartMandate Pydantic model
            cart = CartMandate(
                mandate_id=uuid.uuid4(),
                intent_mandate_id=intent_mandate.mandate_id,
                product_id=product_id,
                price_at_selection=product.get("price", 0),
                coupon_id=coupon_id,
                payable_amount=payable,
            )

            # Persist to DB
            db_cart = DBCartMandate(
                mandate_id=cart.mandate_id,
                intent_mandate_id=cart.intent_mandate_id,
                product_id=cart.product_id,
                coupon_id=cart.coupon_id,
                price_at_selection=cart.price_at_selection,
                payable_amount=cart.payable_amount,
            )
            db.add(db_cart)

            # Evaluate payment authorization
            policy = evaluate_payment_authorization(db, intent_mandate, cart)

            # Enrich product dict
            product["cart_mandate_id"] = str(cart.mandate_id)
            product["payable_amount"] = payable
            product["payment_authorization"] = policy.authorization_type
            product["payment_approved"] = policy.approved
            product["payment_reason"] = policy.reason

            # Resolve merchant name for display
            mid = product.get("merchant_id", "")
            product["merchant_name"] = merchant_names.get(mid, "Unknown Merchant")

            # Coupon display info
            if product.get("applied_coupon"):
                product["coupon_display"] = {
                    "code": product["applied_coupon"].get("code", ""),
                    "discount": product["applied_coupon"].get("discount_amount", 0),
                    "savings_pct": round(
                        (product["applied_coupon"].get("discount_amount", 0)
                         / product.get("price", 1))
                        * 100, 1
                    ),
                }
            else:
                product["coupon_display"] = None

        except Exception as e:
            logger.error("Checkout assembly failed for product %s: %s", product.get("id"), e)
            product["cart_mandate_id"] = None
            product["payment_authorization"] = "rejected"
            product["payment_approved"] = False
            product["payment_reason"] = f"Assembly error: {e}"

    # Commit all CartMandates in one transaction
    try:
        db.commit()
        write_audit_log(
            db, "checkout_assembler", "checkout_assembled",
            intent_mandate.mandate_id,
            {"product_count": len(products)},
            {"products": [p.get("id") for p in products]},
            f"Pre-assembled checkout for {len(products)} products.",
        )
    except Exception as e:
        db.rollback()
        logger.error("Failed to commit checkout assembly: %s", e)
        raise

    return products


# ── Helpers ──────────────────────────────────────────────────────────────

def _persist_intent_mandate(db: Session, intent: IntentMandate) -> None:
    """Upsert IntentMandate so FK constraints on CartMandate are satisfied."""
    existing = (
        db.query(DBIntentMandate)
        .filter_by(mandate_id=intent.mandate_id)
        .first()
    )
    if not existing:
        db_constraints = dict(intent.constraints)
        if intent.autopay_limit is not None:
            db_constraints["_autopay_limit"] = intent.autopay_limit
            
        db_intent = DBIntentMandate(
            mandate_id=intent.mandate_id,
            user_id=intent.user_id,
            category=intent.category,
            constraints=db_constraints,
            completeness=intent.completeness,
        )
        db.add(db_intent)
        db.flush()  # flush so FK is available for CartMandates


def _load_merchant_names(db: Session) -> Dict[str, str]:
    """merchant_id (str) → merchant name."""
    merchants = db.query(Merchant).all()
    return {str(m.merchant_id): m.name for m in merchants}
