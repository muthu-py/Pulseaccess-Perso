"""Subscription database repository for persistence operations."""

import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.subscription.enums import SubscriptionStatus
from app.modules.subscription.models import Subscription


class SubscriptionRepository:
    """Handles database queries and updates for Subscription records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, subscription_id: uuid.UUID) -> Subscription | None:
        """Fetch a subscription by its primary key."""
        stmt = select(Subscription).where(Subscription.id == subscription_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_by_member_and_plan(
        self, member_id: uuid.UUID, plan_id: uuid.UUID
    ) -> Subscription | None:
        """Find an active, non-expired subscription for a member and plan."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(Subscription)
            .where(
                Subscription.member_id == member_id,
                Subscription.plan_id == plan_id,
                Subscription.status == SubscriptionStatus.ACTIVE.value,
                Subscription.ends_at > now,
            )
            .order_by(desc(Subscription.ends_at))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_member_id(self, member_id: uuid.UUID) -> Sequence[Subscription]:
        """List all subscriptions belonging to a member."""
        stmt = (
            select(Subscription)
            .where(Subscription.member_id == member_id)
            .order_by(desc(Subscription.created_at))
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def create(
        self,
        member_id: uuid.UUID,
        plan_id: uuid.UUID,
        starts_at: datetime,
        ends_at: datetime,
        status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
    ) -> Subscription:
        """Persist a new subscription."""
        subscription = Subscription(
            member_id=member_id,
            plan_id=plan_id,
            status=status.value,
            starts_at=starts_at,
            ends_at=ends_at,
        )
        self._session.add(subscription)
        await self._session.flush()
        return subscription

    async def extend_ends_at(
        self, subscription: Subscription, new_ends_at: datetime
    ) -> Subscription:
        """Extend the expiry date and ensure status is active."""
        subscription.ends_at = new_ends_at
        subscription.status = SubscriptionStatus.ACTIVE.value
        subscription.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return subscription

    async def update_status(
        self,
        subscription: Subscription,
        status: SubscriptionStatus,
        cancelled_at: datetime | None = None,
    ) -> Subscription:
        """Update subscription status (e.g. cancelled, expired)."""
        subscription.status = status.value
        if cancelled_at is not None:
            subscription.cancelled_at = cancelled_at
        subscription.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return subscription
