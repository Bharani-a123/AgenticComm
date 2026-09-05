import uuid
from app.protocols.ap2.mandates import CartMandate, PaymentMandate
from app.services.policy_engine import PolicyDecision
from app.protocols.ap2.mandate_hash import derive_idempotency_key

def create_payment_mandate(cart: CartMandate, policy: PolicyDecision) -> PaymentMandate:
    return PaymentMandate(
        mandate_id=uuid.uuid4(),
        cart_mandate_id=cart.mandate_id,
        amount=cart.payable_amount,
        authorization_type=policy.authorization_type,
        idempotency_key=derive_idempotency_key(cart.mandate_id),
    )
