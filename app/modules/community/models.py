"""Community ORM model with Telegram integration columns.

Changes from baseline:
  - telegram_channel_id → telegram_chat_id (Doc 03 §6)
  - Added telegram_connection_status (Doc 03 §6)
  - Added telegram_connected_at (Doc 03 §6)
  - Added is_active, created_at, updated_at (Milestone 1)
  - Added UNIQUE(creator_id, name) constraint (Milestone 1)
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base
from app.modules.telegram.enums import TelegramConnectionStatus


class Community(Base):
    __tablename__ = "communities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        default=None,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Telegram integration columns ─────────────────────────────────
    telegram_chat_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
    )
    telegram_connection_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TelegramConnectionStatus.NOT_CONNECTED.value,
    )
    telegram_connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    __table_args__ = (
        UniqueConstraint("creator_id", "name", name="uq_communities_creator_name"),
        Index("ix_communities_telegram_chat_id", "telegram_chat_id", unique=True),
    )
