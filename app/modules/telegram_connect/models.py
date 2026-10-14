"""Telegram connect ORM models, shared by creators and members."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class TelegramAccount(Base):
    """A verified Telegram account linked to one creator or one member."""

    __tablename__ = "telegram_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    owner_type: Mapped[str] = mapped_column(String(20), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    telegram_user_id: Mapped[str] = mapped_column(String(32), nullable=False)
    telegram_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("owner_type", "owner_id", name="uq_telegram_accounts_owner"),
        UniqueConstraint(
            "owner_type", "telegram_user_id", name="uq_telegram_accounts_owner_type_tg_user",
        ),
        Index("ix_telegram_accounts_telegram_user_id", "telegram_user_id"),
    )


class TelegramLinkToken(Base):
    """One-time code carried in the bot's /start link."""

    __tablename__ = "telegram_link_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    owner_type: Mapped[str] = mapped_column(String(20), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # Set when the user taps Start, so the follow-up contact message can be
    # matched to this token without keeping conversation state in memory.
    telegram_user_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_telegram_link_tokens_telegram_user_id", "telegram_user_id"),
    )
