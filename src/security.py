import hashlib
import hmac

SIGNATURE_HEADER = "Ashby-Signature"


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify an Ashby webhook's HMAC-SHA256 signature over the raw body."""
    if not signature or not secret:
        return False

    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    try:
        return hmac.compare_digest(expected, signature)
    except (TypeError, ValueError):
        return False
