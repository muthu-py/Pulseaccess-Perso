import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Creator, LoginOTP, RefreshToken


# ======================================================================
# Creator Repository
# ======================================================================

class CreatorRepository:
    """Data access layer for the Creator model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        name: str,
        username: str,
        email: str,
        phone: str | None = None,
    ) -> Creator:
        """Insert a new creator record."""
        creator = Creator(
            name=name,
            username=username,
            email=email.lower(),
            phone=phone,
        )
        self._session.add(creator)
        await self._session.flush()
        return creator

    async def get_by_id(self, creator_id: uuid.UUID) -> Creator | None:
        """Fetch a creator by primary key."""
        stmt = select(Creator).where(Creator.id == creator_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Creator | None:
        """Fetch a creator by email (case-insensitive)."""
        stmt = select(Creator).where(Creator.email == email.lower())
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Creator | None:
        """Fetch a creator by username."""
        stmt = select(Creator).where(Creator.username == username)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_identifier(self, identifier: str) -> Creator | None:
        """Fetch a creator by email or username."""
        # Try email first, then username
        creator = await self.get_by_email(identifier)
        if creator is None:
            creator = await self.get_by_username(identifier)
        return creator

    async def exists_email(self, email: str) -> bool:
        """Check if a creator with this email exists."""
        stmt = select(Creator.id).where(Creator.email == email.lower())
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def exists_phone(self, phone: str) -> bool:
        """Check if a creator with this phone exists."""
        stmt = select(Creator.id).where(Creator.phone == phone)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def update_phone(self, creator_id: uuid.UUID, phone: str) -> None:
        """Set a creator's phone number."""
        stmt = update(Creator).where(Creator.id == creator_id).values(phone=phone)
        await self._session.execute(stmt)

    async def exists_username(self, username: str) -> bool:
        """Check if a creator with this username exists."""
        stmt = select(Creator.id).where(Creator.username == username)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None


# ======================================================================
# OTP Repository
# ======================================================================

class OTPRepository:
    """Data access layer for the LoginOTP model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        creator_id: uuid.UUID,
        otp_hash: str,
        purpose: str,
        expires_at: datetime,
    ) -> LoginOTP:
        """Insert a new OTP record."""
        otp = LoginOTP(
            creator_id=creator_id,
            otp_hash=otp_hash,
            purpose=purpose,
            expires_at=expires_at,
        )
        self._session.add(otp)
        await self._session.flush()
        return otp

    async def get_active(
        self,
        creator_id: uuid.UUID,
        purpose: str = "login",
    ) -> LoginOTP | None:
        """Fetch the active (unused, not-expired) OTP for a creator."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(LoginOTP)
            .where(
                LoginOTP.creator_id == creator_id,
                LoginOTP.purpose == purpose,
                LoginOTP.used_at.is_(None),
                LoginOTP.expires_at > now,
            )
            .order_by(LoginOTP.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def invalidate_active(
        self,
        creator_id: uuid.UUID,
        purpose: str = "login",
    ) -> None:
        """Mark all active OTPs for a creator as used (invalidated)."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(LoginOTP)
            .where(
                LoginOTP.creator_id == creator_id,
                LoginOTP.purpose == purpose,
                LoginOTP.used_at.is_(None),
            )
            .values(used_at=now)
        )
        await self._session.execute(stmt)

    async def increment_attempts(self, otp_id: uuid.UUID) -> None:
        """Increment the attempt counter for an OTP."""
        stmt = (
            update(LoginOTP)
            .where(LoginOTP.id == otp_id)
            .values(attempts=LoginOTP.attempts + 1)
        )
        await self._session.execute(stmt)

    async def mark_used(self, otp_id: uuid.UUID) -> None:
        """Mark an OTP as used."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(LoginOTP)
            .where(LoginOTP.id == otp_id)
            .values(used_at=now)
        )
        await self._session.execute(stmt)

    async def delete_expired(self) -> int:
        """Delete all expired OTPs. Returns the number of deleted rows."""
        now = datetime.now(timezone.utc)
        stmt = select(LoginOTP).where(LoginOTP.expires_at <= now)
        result = await self._session.execute(stmt)
        expired = result.scalars().all()
        count = len(expired)
        for otp in expired:
            await self._session.delete(otp)
        return count


# ======================================================================
# Refresh Token Repository
# ======================================================================

class RefreshTokenRepository:
    """Data access layer for the RefreshToken model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        creator_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        """Insert a new refresh token record."""
        token = RefreshToken(
            creator_id=creator_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self._session.add(token)
        await self._session.flush()
        return token

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Fetch a refresh token by its hash."""
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, token_id: uuid.UUID) -> None:
        """Revoke a single refresh token by setting revoked_at."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(revoked_at=now)
        )
        await self._session.execute(stmt)

    async def revoke_all(self, creator_id: uuid.UUID) -> None:
        """Revoke all active refresh tokens for a creator."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.creator_id == creator_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        await self._session.execute(stmt)

    async def delete_expired(self) -> int:
        """Delete all expired refresh tokens. Returns the number of deleted rows."""
        now = datetime.now(timezone.utc)
        stmt = select(RefreshToken).where(RefreshToken.expires_at <= now)
        result = await self._session.execute(stmt)
        expired = result.scalars().all()
        count = len(expired)
        for token in expired:
            await self._session.delete(token)
        return count
