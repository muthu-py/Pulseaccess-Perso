import hashlib
import hmac
import secrets
import string


class SecurityService:
    """Reusable cryptographic utilities for OTP generation, hashing, and verification."""

    def __init__(self, otp_hash_secret: str) -> None:
        self._otp_hash_secret = otp_hash_secret

    def generate_otp(self, length: int = 6) -> str:
        """Generate a cryptographically secure numeric OTP of the given length."""
        digits = string.digits
        return "".join(secrets.choice(digits) for _ in range(length))

    def hash_value(self, value: str) -> str:
        """Create an HMAC-SHA256 hex digest of the given value."""
        return hmac.HMAC(
            key=self._otp_hash_secret.encode("utf-8"),
            msg=value.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

    def verify_hash(self, value: str, hashed: str) -> bool:
        """Verify a value against its HMAC-SHA256 hash using constant-time comparison."""
        computed = self.hash_value(value)
        return hmac.compare_digest(computed, hashed)

    def generate_random_string(self, length: int = 64) -> str:
        """Generate a URL-safe random string suitable for tokens."""
        return secrets.token_urlsafe(length)
