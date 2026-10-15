"""Member module repository — persistence only."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.member.models import Member, MemberLoginOTP


class MemberRepository:
    """Data access layer for members and their login OTPs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Members ──────────────────────────────────────────────────────

    async def create(self, name: str, phone: str, email: str) -> Member:
        member = Member(name=name, phone=phone, email=email.lower())
        self._session.add(member)
        await self._session.flush()
        return member

    async def get_by_id(self, member_id: uuid.UUID) -> Member | None:
        result = await self._session.execute(select(Member).where(Member.id == member_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Member | None:
        result = await self._session.execute(
            select(Member).where(Member.email == email.lower()),
        )
        return result.scalar_one_or_none()

    async def exists_email(self, email: str) -> bool:
        return await self.get_by_email(email) is not None

    async def exists_phone(self, phone: str) -> bool:
        result = await self._session.execute(select(Member.id).where(Member.phone == phone))
        return result.scalar_one_or_none() is not None

    # ── Login OTPs ───────────────────────────────────────────────────

    async def create_otp(
        self,
        member_id: uuid.UUID,
        otp_hash: str,
        expires_at: datetime,
    ) -> MemberLoginOTP:
        otp = MemberLoginOTP(member_id=member_id, otp_hash=otp_hash, expires_at=expires_at)
        self._session.add(otp)
        await self._session.flush()
        return otp

    async def get_active_otp(self, member_id: uuid.UUID) -> MemberLoginOTP | None:
        stmt = (
            select(MemberLoginOTP)
            .where(
                MemberLoginOTP.member_id == member_id,
                MemberLoginOTP.used_at.is_(None),
            )
            .order_by(MemberLoginOTP.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_otps_since(self, member_id: uuid.UUID, since: datetime) -> int:
        stmt = select(func.count(MemberLoginOTP.id)).where(
            MemberLoginOTP.member_id == member_id,
            MemberLoginOTP.created_at >= since,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def invalidate_active_otps(self, member_id: uuid.UUID) -> None:
        stmt = (
            update(MemberLoginOTP)
            .where(
                MemberLoginOTP.member_id == member_id,
                MemberLoginOTP.used_at.is_(None),
            )
            .values(used_at=datetime.now(timezone.utc))
        )
        await self._session.execute(stmt)

    async def increment_otp_attempts(self, otp_id: uuid.UUID) -> None:
        stmt = (
            update(MemberLoginOTP)
            .where(MemberLoginOTP.id == otp_id)
            .values(attempts=MemberLoginOTP.attempts + 1)
        )
        await self._session.execute(stmt)

    async def mark_otp_used(self, otp_id: uuid.UUID) -> None:
        stmt = (
            update(MemberLoginOTP)
            .where(MemberLoginOTP.id == otp_id)
            .values(used_at=datetime.now(timezone.utc))
        )
        await self._session.execute(stmt)

    async def commit(self) -> None:
        await self._session.commit()
