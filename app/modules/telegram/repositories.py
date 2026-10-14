"""Telegram module repository — persistence layer.

Handles all database operations for telegram-related data:
community Telegram state, operation queue, and member lookups.
Contains NO business logic, NO external HTTP calls (Doc 05 §7).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.community.models import Community
from app.modules.member.models import Member
from app.modules.telegram.enums import (
    TelegramConnectionStatus,
    TelegramOperationStatus,
    TelegramOperationType,
)
from app.modules.telegram.models import TelegramOperation
from app.modules.telegram_connect.enums import OwnerType
from app.modules.telegram_connect.models import TelegramAccount


class TelegramRepository:
    """Data access layer for Telegram integration persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Community queries ────────────────────────────────────────────

    async def get_community_by_id(self, community_id: uuid.UUID) -> Community | None:
        stmt = select(Community).where(Community.id == community_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_community_by_chat_id(self, chat_id: str) -> Community | None:
        stmt = select(Community).where(Community.telegram_chat_id == chat_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def save_chat_id(
        self,
        community_id: uuid.UUID,
        chat_id: str,
    ) -> None:
        stmt = (
            update(Community)
            .where(Community.id == community_id)
            .values(telegram_chat_id=chat_id)
        )
        await self._session.execute(stmt)

    async def update_connection_status(
        self,
        community_id: uuid.UUID,
        status: TelegramConnectionStatus,
    ) -> None:
        stmt = (
            update(Community)
            .where(Community.id == community_id)
            .values(telegram_connection_status=status.value)
        )
        await self._session.execute(stmt)

    async def mark_connected(self, community_id: uuid.UUID, chat_id: str) -> None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(Community)
            .where(Community.id == community_id)
            .values(
                telegram_chat_id=chat_id,
                telegram_connection_status=TelegramConnectionStatus.CONNECTED.value,
                telegram_connected_at=now,
            )
        )
        await self._session.execute(stmt)

    async def mark_disconnected(self, community_id: uuid.UUID) -> None:
        stmt = (
            update(Community)
            .where(Community.id == community_id)
            .values(
                telegram_chat_id=None,
                telegram_connection_status=TelegramConnectionStatus.DISCONNECTED.value,
                telegram_connected_at=None,
            )
        )
        await self._session.execute(stmt)

    # ── Member queries ───────────────────────────────────────────────

    async def get_member_by_id(self, member_id: uuid.UUID) -> Member | None:
        stmt = select(Member).where(Member.id == member_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_member_telegram_id(self, member_id: uuid.UUID) -> str | None:
        """Telegram user ID the member connected, if any."""
        stmt = select(TelegramAccount.telegram_user_id).where(
            TelegramAccount.owner_type == OwnerType.MEMBER.value,
            TelegramAccount.owner_id == member_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_member_by_telegram_id(self, telegram_user_id: str) -> Member | None:
        stmt = (
            select(Member)
            .join(
                TelegramAccount,
                (TelegramAccount.owner_id == Member.id)
                & (TelegramAccount.owner_type == OwnerType.MEMBER.value),
            )
            .where(TelegramAccount.telegram_user_id == telegram_user_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ── Operation queue ──────────────────────────────────────────────

    async def create_operation(
        self,
        operation_type: TelegramOperationType,
        community_id: uuid.UUID,
        member_id: uuid.UUID | None = None,
        scheduled_at: datetime | None = None,
    ) -> TelegramOperation:
        op = TelegramOperation(
            operation_type=operation_type.value,
            community_id=community_id,
            member_id=member_id,
            status=TelegramOperationStatus.PENDING.value,
            scheduled_at=scheduled_at,
        )
        self._session.add(op)
        await self._session.flush()
        return op

    async def update_operation_status(
        self,
        operation_id: uuid.UUID,
        status: TelegramOperationStatus,
        last_error: str | None = None,
    ) -> None:
        values: dict = {"status": status.value}
        if last_error is not None:
            values["last_error"] = last_error
        if status == TelegramOperationStatus.COMPLETED:
            values["completed_at"] = datetime.now(timezone.utc)
        stmt = (
            update(TelegramOperation)
            .where(TelegramOperation.id == operation_id)
            .values(**values)
        )
        await self._session.execute(stmt)

    async def mark_completed(self, operation_id: uuid.UUID) -> None:
        await self.update_operation_status(
            operation_id,
            TelegramOperationStatus.COMPLETED,
        )

    async def mark_failed(
        self,
        operation_id: uuid.UUID,
        error: str | None = None,
    ) -> None:
        await self.update_operation_status(
            operation_id,
            TelegramOperationStatus.FAILED,
            last_error=error,
        )

    async def increment_retry(
        self,
        operation_id: uuid.UUID,
        scheduled_at: datetime,
        error: str | None = None,
    ) -> None:
        values: dict = {
            "status": TelegramOperationStatus.RETRYING.value,
            "retry_count": TelegramOperation.retry_count + 1,
            "scheduled_at": scheduled_at,
        }
        if error:
            values["last_error"] = error
        stmt = (
            update(TelegramOperation)
            .where(TelegramOperation.id == operation_id)
            .values(**values)
        )
        await self._session.execute(stmt)

    async def find_pending(self) -> Sequence[TelegramOperation]:
        now = datetime.now(timezone.utc)
        stmt = (
            select(TelegramOperation)
            .where(
                TelegramOperation.status.in_([
                    TelegramOperationStatus.PENDING.value,
                    TelegramOperationStatus.RETRYING.value,
                ]),
                (TelegramOperation.scheduled_at.is_(None))
                | (TelegramOperation.scheduled_at <= now),
            )
            .order_by(TelegramOperation.created_at.asc())
            .limit(50)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def find_retryable(self, max_retries: int = 5) -> Sequence[TelegramOperation]:
        now = datetime.now(timezone.utc)
        stmt = (
            select(TelegramOperation)
            .where(
                TelegramOperation.status == TelegramOperationStatus.RETRYING.value,
                TelegramOperation.retry_count < max_retries,
                (TelegramOperation.scheduled_at.is_(None))
                | (TelegramOperation.scheduled_at <= now),
            )
            .order_by(TelegramOperation.scheduled_at.asc())
            .limit(50)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_connected_communities(self) -> Sequence[Community]:
        stmt = select(Community).where(
            Community.telegram_connection_status == TelegramConnectionStatus.CONNECTED.value,
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()
