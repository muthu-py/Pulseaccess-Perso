"""Payment models for tracking Razorpay orders and webhook events."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base
from app.modules.payment.enums import PaymentEventStatus, PaymentOrderStatus


class PaymentOrder(Base):
    """Represents a Razorpay payment order created for a plan purchase."""

    __tablename__ = "payment_orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    razorpay_order_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    amount_paise: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="INR",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=PaymentOrderStatus.CREATED.value,
    )
    receipt_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
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

    __table_args__ = (
        Index("ix_payment_orders_razorpay_order_id", "razorpay_order_id"),
        Index("ix_payment_orders_member_id", "member_id"),
        Index("ix_payment_orders_plan_id", "plan_id"),
        Index("ix_payment_orders_status", "status"),
    )


class PaymentEvent(Base):
    """Raw record of received Razorpay webhook events for audit and idempotency."""

    __tablename__ = "payment_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    event_id: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
        default=None,
    )
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="unknown",
    )
    payload: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=PaymentEventStatus.PROCESSED.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_payment_events_event_id", "event_id"),
        Index("ix_payment_events_event_type", "event_type"),
    )
