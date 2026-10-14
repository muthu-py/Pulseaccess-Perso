"""Payment database repository for orders and webhook events."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.payment.enums import PaymentEventStatus, PaymentOrderStatus
from app.modules.community.models import Community
from app.modules.member.models import Member
from app.modules.payment.models import PaymentEvent, PaymentOrder
from app.modules.plan.models import Plan


class PaymentRepository:
    """Handles database persistence for payment orders and webhook audit events."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_plan_by_id(self, plan_id: uuid.UUID) -> Plan | None:
        """Fetch plan to check price and details."""
        stmt = select(Plan).where(Plan.id == plan_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_community(self, community_id: uuid.UUID) -> Community | None:
        result = await self._session.execute(
            select(Community).where(Community.id == community_id)
        )
        return result.scalar_one_or_none()

    async def get_member(self, member_id: uuid.UUID) -> Member | None:
        result = await self._session.execute(select(Member).where(Member.id == member_id))
        return result.scalar_one_or_none()

    async def get_open_link(
        self,
        member_id: uuid.UUID,
        plan_id: uuid.UUID,
        valid_after: datetime,
    ) -> PaymentOrder | None:
        """Newest unpaid payment link of this member for this plan, still valid."""
        stmt = (
            select(PaymentOrder)
            .where(
                PaymentOrder.member_id == member_id,
                PaymentOrder.plan_id == plan_id,
                PaymentOrder.status == PaymentOrderStatus.CREATED.value,
                PaymentOrder.razorpay_payment_link_id.is_not(None),
                PaymentOrder.expires_at > valid_after,
            )
            .order_by(PaymentOrder.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_order(self, order: PaymentOrder) -> PaymentOrder:
        self._session.add(order)
        await self._session.flush()
        return order

    async def save_order(self, order: PaymentOrder) -> PaymentOrder:
        order.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return order

    async def get_order_by_payment_link_id(self, payment_link_id: str) -> PaymentOrder | None:
        result = await self._session.execute(
            select(PaymentOrder).where(PaymentOrder.razorpay_payment_link_id == payment_link_id)
        )
        return result.scalar_one_or_none()

    async def get_order_by_id(self, order_id: uuid.UUID) -> PaymentOrder | None:
        """Fetch payment order by internal UUID primary key."""
        stmt = select(PaymentOrder).where(PaymentOrder.id == order_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_order_by_razorpay_id(
        self, razorpay_order_id: str
    ) -> PaymentOrder | None:
        """Fetch payment order by Razorpay order ID (e.g. order_xxx)."""
        stmt = select(PaymentOrder).where(
            PaymentOrder.razorpay_order_id == razorpay_order_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_order_status(
        self, order: PaymentOrder, status: PaymentOrderStatus
    ) -> PaymentOrder:
        """Update payment order status (e.g. paid, failed)."""
        order.status = status.value
        order.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return order

    async def get_event_by_id(self, event_id: str) -> PaymentEvent | None:
        """Find webhook event by event_id for idempotency check."""
        stmt = select(PaymentEvent).where(PaymentEvent.event_id == event_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def record_event(
        self,
        event_id: str | None,
        event_type: str,
        payload: str,
        status: PaymentEventStatus = PaymentEventStatus.PROCESSED,
    ) -> PaymentEvent:
        """Log a received webhook event payload."""
        event = PaymentEvent(
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            status=status.value,
        )
        self._session.add(event)
        await self._session.flush()
        return event
