import hmac
import hashlib
from app.core.config import get_settings

def verify_webhook_signature(raw_body: bytes, received_signature: str) -> bool:
    """
    Recomputes the HMAC-SHA256 signature using the webhook secret
    and compares it to X-Razorpay-Signature in constant time.
    """
    settings = get_settings()
    secret = settings.razorpay_webhook_secret.get_secret_value().encode("utf-8")
    
    expected_signature = hmac.new(
        key=secret,
        msg=raw_body,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, received_signature)
