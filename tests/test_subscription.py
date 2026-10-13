import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.subscription.enums import SubscriptionStatus
from app.modules.subscription.exceptions import (
    SubscriptionAlreadyCancelledError,
    SubscriptionNotFoundError,
)
from app.modules.subscription.repositories import SubscriptionRepository
from app.modules.subscription.services import SubscriptionService


@pytest.mark.asyncio
async def test_activate_and_renew_subscription(db_session: AsyncSession):
    repo = SubscriptionRepository(db_session)
    service = SubscriptionService(repo)

    member_id = uuid.uuid4()
    plan_id = uuid.uuid4()

    # 1. Activate new subscription
    sub1 = await service.activate_or_renew(member_id, plan_id, duration_days=30)
    assert sub1.member_id == member_id
    assert sub1.plan_id == plan_id
    assert sub1.status == SubscriptionStatus.ACTIVE.value
    assert sub1.ends_at > sub1.starts_at

    # 2. Check active
    is_active = await service.is_member_active(member_id, plan_id)
    assert is_active is True

    # 3. Renew existing active subscription
    initial_ends_at = sub1.ends_at
    sub2 = await service.activate_or_renew(member_id, plan_id, duration_days=15)
    assert sub2.id == sub1.id
    assert sub2.ends_at > initial_ends_at


@pytest.mark.asyncio
async def test_cancel_subscription(db_session: AsyncSession):
    repo = SubscriptionRepository(db_session)
    service = SubscriptionService(repo)

    member_id = uuid.uuid4()
    plan_id = uuid.uuid4()

    sub = await service.activate_or_renew(member_id, plan_id, duration_days=30)
    assert sub.status == SubscriptionStatus.ACTIVE.value

    # Cancel
    cancelled = await service.cancel_subscription(sub.id)
    assert cancelled.status == SubscriptionStatus.CANCELLED.value
    assert cancelled.cancelled_at is not None

    # Should not be active anymore
    is_active = await service.is_member_active(member_id, plan_id)
    assert is_active is False

    # Attempt to cancel again should raise
    with pytest.raises(SubscriptionAlreadyCancelledError):
        await service.cancel_subscription(sub.id)


@pytest.mark.asyncio
async def test_get_nonexistent_subscription_raises(db_session: AsyncSession):
    repo = SubscriptionRepository(db_session)
    service = SubscriptionService(repo)

    with pytest.raises(SubscriptionNotFoundError):
        await service.get_subscription(uuid.uuid4())


@pytest.mark.asyncio
async def test_subscription_api_flow(async_client: AsyncClient):
    member_id = str(uuid.uuid4())
    plan_id = str(uuid.uuid4())

    # 1. Create subscription via API
    res = await async_client.post(
        "/api/v1/subscriptions",
        json={"member_id": member_id, "plan_id": plan_id, "duration_days": 30},
    )
    assert res.status_code == 201
    data = res.json()["data"]
    sub_id = data["id"]
    assert data["status"] == "active"
    assert data["member_id"] == member_id

    # 2. Fetch subscription
    res = await async_client.get(f"/api/v1/subscriptions/{sub_id}")
    assert res.status_code == 200
    assert res.json()["data"]["id"] == sub_id

    # 3. Extend subscription
    res = await async_client.post(
        f"/api/v1/subscriptions/{sub_id}/extend",
        json={"days": 10},
    )
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "active"

    # 4. List subscriptions for member
    res = await async_client.get(f"/api/v1/subscriptions/member/{member_id}")
    assert res.status_code == 200
    assert res.json()["data"]["total"] >= 1

    # 5. Cancel subscription
    res = await async_client.post(f"/api/v1/subscriptions/{sub_id}/cancel")
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "cancelled"
