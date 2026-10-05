import hashlib
import hmac

SIGNATURE_HEADER = "Ashby-Signature"


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify an Ashby webhook's HMAC-SHA256 signature over the raw body."""
    if not signature or not secret:
        return False

    # Ashby sends the digest as "sha256=<hex>"; accept the bare hex form too.
    if signature.startswith("sha256="):
        signature = signature[len("sha256="):]

    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    try:
        return hmac.compare_digest(expected, signature)
    except (TypeError, ValueError):
        return False
