from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class JWTService:
    """Handles creation, decoding, and validation of JWT tokens."""

    def __init__(self, settings: Settings) -> None:
        self._secret_key = settings.JWT_SECRET_KEY
        self._algorithm = settings.JWT_ALGORITHM
        self._access_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self._refresh_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS

    def create_access_token(
        self,
        subject: str,
        extra_claims: dict[str, Any] | None = None,
    ) -> str:
        """Create a short-lived access token."""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self._access_expire_minutes)

        claims: dict[str, Any] = {
            "sub": subject,
            "iat": now,
            "exp": expire,
            "type": "access",
        }
        if extra_claims:
            claims.update(extra_claims)

        return jwt.encode(claims, self._secret_key, algorithm=self._algorithm)

    def create_refresh_token(self, subject: str) -> str:
        """Create a long-lived refresh token."""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self._refresh_expire_days)

        claims: dict[str, Any] = {
            "sub": subject,
            "iat": now,
            "exp": expire,
            "type": "refresh",
        }

        return jwt.encode(claims, self._secret_key, algorithm=self._algorithm)

    def decode_token(self, token: str) -> dict[str, Any]:
        """Decode a JWT token and return its claims. Raises JWTError on failure."""
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
            )
            return payload
        except JWTError as exc:
            logger.warning("JWT decode failed: %s", str(exc))
            raise

    def validate_token(self, token: str) -> dict[str, Any]:
        """Decode and validate a JWT token, checking expiry. Returns claims."""
        payload = self.decode_token(token)

        exp = payload.get("exp")
        if exp is None:
            raise JWTError("Token has no expiration claim")

        # python-jose already checks expiry during decode, but be explicit
        exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
        if exp_dt < datetime.now(timezone.utc):
            raise JWTError("Token has expired")

        return payload
