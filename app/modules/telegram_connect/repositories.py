"""Telegram connect repository — persistence only."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Creator
from app.modules.member.models import Member
from app.modules.telegram_connect.enums import OwnerType
from app.modules.telegram_connect.models import TelegramAccount, TelegramLinkToken


class TelegramConnectRepository:
    """Data access for Telegram accounts and link tokens."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Owners ───────────────────────────────────────────────────────

    async def get_owner_phone(self, owner_type: OwnerType, owner_id: uuid.UUID) -> str | None:
        model = Creator if owner_type == OwnerType.CREATOR else Member
        result = await self._session.execute(select(model.phone).where(model.id == owner_id))
        return result.scalar_one_or_none()

    # ── Accounts ─────────────────────────────────────────────────────

    async def get_account(
        self,
        owner_type: OwnerType,
        owner_id: uuid.UUID,
    ) -> TelegramAccount | None:
        stmt = select(TelegramAccount).where(
            TelegramAccount.owner_type == owner_type.value,
            TelegramAccount.owner_id == owner_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_account_by_telegram_id(
        self,
        owner_type: OwnerType,
        telegram_user_id: str,
    ) -> TelegramAccount | None:
        stmt = select(TelegramAccount).where(
            TelegramAccount.owner_type == owner_type.value,
            TelegramAccount.telegram_user_id == telegram_user_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_account(
        self,
        owner_type: OwnerType,
        owner_id: uuid.UUID,
        telegram_user_id: str,
        telegram_username: str | None,
        phone: str,
    ) -> TelegramAccount:
        account = TelegramAccount(
            owner_type=owner_type.value,
            owner_id=owner_id,
            telegram_user_id=telegram_user_id,
            telegram_username=telegram_username,
            phone=phone,
        )
        self._session.add(account)
        await self._session.flush()
        return account

    # ── Link tokens ──────────────────────────────────────────────────

    async def create_token(
        self,
        token_hash: str,
        owner_type: OwnerType,
        owner_id: uuid.UUID,
        expires_at: datetime,
    ) -> TelegramLinkToken:
        token = TelegramLinkToken(
            token_hash=token_hash,
            owner_type=owner_type.value,
            owner_id=owner_id,
            expires_at=expires_at,
        )
        self._session.add(token)
        await self._session.flush()
        return token

    async def get_token_by_hash(self, token_hash: str) -> TelegramLinkToken | None:
        result = await self._session.execute(
            select(TelegramLinkToken).where(TelegramLinkToken.token_hash == token_hash),
        )
        return result.scalar_one_or_none()

    async def get_pending_token_for_telegram_user(
        self,
        telegram_user_id: str,
    ) -> TelegramLinkToken | None:
        """Latest unused, unexpired token this Telegram user tapped Start on."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(TelegramLinkToken)
            .where(
                TelegramLinkToken.telegram_user_id == telegram_user_id,
                TelegramLinkToken.used_at.is_(None),
                TelegramLinkToken.expires_at > now,
            )
            .order_by(TelegramLinkToken.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def claim_token(self, token_id: uuid.UUID, telegram_user_id: str) -> None:
        await self._session.execute(
            update(TelegramLinkToken)
            .where(TelegramLinkToken.id == token_id)
            .values(telegram_user_id=telegram_user_id),
        )

    async def mark_token_used(self, token_id: uuid.UUID) -> None:
        await self._session.execute(
            update(TelegramLinkToken)
            .where(TelegramLinkToken.id == token_id)
            .values(used_at=datetime.now(timezone.utc)),
        )

    async def invalidate_tokens(self, owner_type: OwnerType, owner_id: uuid.UUID) -> None:
        """Expire earlier unused tokens so only the newest link works."""
        await self._session.execute(
            update(TelegramLinkToken)
            .where(
                TelegramLinkToken.owner_type == owner_type.value,
                TelegramLinkToken.owner_id == owner_id,
                TelegramLinkToken.used_at.is_(None),
            )
            .values(used_at=datetime.now(timezone.utc)),
        )
