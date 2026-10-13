"""Subscription service managing lifecycle, activations, renewals, and cancellations."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Sequence

from app.modules.subscription.enums import SubscriptionStatus
from app.modules.subscription.exceptions import (
    SubscriptionAlreadyCancelledError,
    SubscriptionNotFoundError,
)
from app.modules.subscription.models import Subscription
from app.modules.subscription.repositories import SubscriptionRepository


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime has UTC timezone info."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class SubscriptionService:
    """Business logic for subscription management."""

    def __init__(self, repository: SubscriptionRepository) -> None:
        self._repo = repository

    async def get_subscription(self, subscription_id: uuid.UUID) -> Subscription:
        """Fetch subscription or raise 404 if not found."""
        subscription = await self._repo.get_by_id(subscription_id)
        if subscription is None:
            raise SubscriptionNotFoundError()
        return subscription

    async def get_member_subscriptions(
        self, member_id: uuid.UUID
    ) -> Sequence[Subscription]:
        """Retrieve all subscription records for a member."""
        return await self._repo.get_by_member_id(member_id)

    async def is_member_active(
        self, member_id: uuid.UUID, plan_id: uuid.UUID
    ) -> bool:
        """Check if a member currently has a valid, non-expired subscription."""
        active = await self._repo.get_active_by_member_and_plan(member_id, plan_id)
        return active is not None

    async def activate_or_renew(
        self,
        member_id: uuid.UUID,
        plan_id: uuid.UUID,
        duration_days: int = 30,
    ) -> Subscription:
        """Create a new subscription or extend an active one upon payment capture."""
        now = datetime.now(timezone.utc)
        existing = await self._repo.get_active_by_member_and_plan(member_id, plan_id)

        if existing is not None:
            ends_at = _ensure_utc(existing.ends_at)
            base_date = max(ends_at, now)
            new_ends_at = base_date + timedelta(days=duration_days)
            return await self._repo.extend_ends_at(existing, new_ends_at)

        ends_at = now + timedelta(days=duration_days)
        return await self._repo.create(
            member_id=member_id,
            plan_id=plan_id,
            starts_at=now,
            ends_at=ends_at,
            status=SubscriptionStatus.ACTIVE,
        )

    async def extend_subscription(
        self, subscription_id: uuid.UUID, days: int
    ) -> Subscription:
        """Extend an existing subscription by a specified number of days."""
        subscription = await self.get_subscription(subscription_id)
        now = datetime.now(timezone.utc)
        ends_at = _ensure_utc(subscription.ends_at)
        base_date = max(ends_at, now)
        new_ends_at = base_date + timedelta(days=days)
        return await self._repo.extend_ends_at(subscription, new_ends_at)

    async def cancel_subscription(self, subscription_id: uuid.UUID) -> Subscription:
        """Cancel an active subscription."""
        subscription = await self.get_subscription(subscription_id)
        if subscription.status == SubscriptionStatus.CANCELLED.value:
            raise SubscriptionAlreadyCancelledError()

        now = datetime.now(timezone.utc)
        return await self._repo.update_status(
            subscription=subscription,
            status=SubscriptionStatus.CANCELLED,
            cancelled_at=now,
        )
