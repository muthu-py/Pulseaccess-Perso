import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Response
from jose import JWTError

from app.core.config import Settings
from app.core.exceptions import (
    InvalidRefreshTokenError,
    RefreshTokenExpiredError,
    RefreshTokenRevokedError,
)
from app.core.logging import get_logger
from app.core.security import SecurityService
from app.infrastructure.security.cookie_service import CookieService
from app.infrastructure.security.jwt_service import JWTService
from app.modules.auth.models import RefreshToken

logger = get_logger(__name__)


class SessionService:
    """Manages login sessions: create, rotate, validate, and revoke refresh tokens."""

    def __init__(
        self,
        jwt_service: JWTService,
        security_service: SecurityService,
        cookie_service: CookieService,
        refresh_token_repo: "RefreshTokenRepository",  # noqa: F821
        settings: Settings,
    ) -> None:
        self._jwt = jwt_service
        self._security = security_service
        self._cookie = cookie_service
        self._refresh_repo = refresh_token_repo
        self._refresh_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS

    async def create_session(
        self,
        creator_id: uuid.UUID,
        response: Response,
    ) -> str:
        """
        Create a new login session.

        Returns the access token (string).
        The refresh token is set as an HttpOnly cookie on the response.
        """
        # Generate tokens
        subject = str(creator_id)
        access_token = self._jwt.create_access_token(
            subject=subject,
            extra_claims={"role": "creator"},
        )
        raw_refresh_token = self._jwt.create_refresh_token(subject=subject)

        # Hash and persist refresh token
        token_hash = self._security.hash_value(raw_refresh_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=self._refresh_expire_days)

        await self._refresh_repo.create(
            creator_id=creator_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        # Set cookie
        self._cookie.set_refresh_cookie(
            response=response,
            token=raw_refresh_token,
            max_age_days=self._refresh_expire_days,
        )

        logger.info("Session created for creator %s", creator_id)
        return access_token

    async def rotate_session(
        self,
        raw_token: str,
        response: Response,
    ) -> str:
        """
        Rotate a refresh token: revoke the old one, issue new access + refresh tokens.

        Returns the new access token.
        The new refresh token is set as an HttpOnly cookie.
        """
        # Validate the current refresh token
        stored_token = await self.validate_refresh_token(raw_token)
        creator_id = stored_token.creator_id

        # Revoke old token
        await self._refresh_repo.revoke(stored_token.id)

        # Create new session
        access_token = await self.create_session(
            creator_id=creator_id,
            response=response,
        )

        logger.info("Refresh token rotated for creator %s", creator_id)
        return access_token

    async def validate_refresh_token(self, raw_token: str) -> RefreshToken:
        """
        Validate a raw refresh token string.

        Checks: JWT validity, existence in DB, not revoked, not expired.
        Returns the stored RefreshToken model.
        """
        # Verify the JWT structure first
        try:
            self._jwt.validate_token(raw_token)
        except JWTError:
            raise InvalidRefreshTokenError()

        # Look up by hash
        token_hash = self._security.hash_value(raw_token)
        stored_token = await self._refresh_repo.get_by_hash(token_hash)

        if stored_token is None:
            raise InvalidRefreshTokenError()

        if stored_token.revoked_at is not None:
            raise RefreshTokenRevokedError()

        if stored_token.expires_at < datetime.now(timezone.utc):
            raise RefreshTokenExpiredError()

        return stored_token

    async def revoke_session(self, raw_token: str) -> None:
        """Revoke a single refresh token."""
        token_hash = self._security.hash_value(raw_token)
        stored_token = await self._refresh_repo.get_by_hash(token_hash)
        if stored_token is not None:
            await self._refresh_repo.revoke(stored_token.id)
            logger.info("Session revoked for creator %s", stored_token.creator_id)

    async def revoke_all_sessions(self, creator_id: uuid.UUID) -> None:
        """Revoke all refresh tokens for a given creator."""
        await self._refresh_repo.revoke_all(creator_id)
        logger.info("All sessions revoked for creator %s", creator_id)
