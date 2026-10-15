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
from tests.helpers import auth_headers, make_member


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
async def test_subscription_api_is_read_only_and_member_scoped(
    async_client: AsyncClient, db_session: AsyncSession,
):
    owner = await make_member(db_session)
    other = await make_member(db_session)
    sub = await SubscriptionService(SubscriptionRepository(db_session)).activate_or_renew(
        member_id=owner.id, plan_id=uuid.uuid4(), duration_days=30,
    )

    # Nobody can create, extend or cancel a subscription over the API:
    # only a paid Razorpay webhook does that.
    res = await async_client.post(
        "/api/v1/subscriptions",
        json={"member_id": str(owner.id), "plan_id": str(uuid.uuid4()), "duration_days": 30},
        headers=auth_headers(owner.id, "member"),
    )
    assert res.status_code in (404, 405)
    for path in (f"/api/v1/subscriptions/{sub.id}/extend", f"/api/v1/subscriptions/{sub.id}/cancel"):
        res = await async_client.post(path, json={"days": 10}, headers=auth_headers(owner.id, "member"))
        assert res.status_code in (404, 405)

    # Login required
    assert (await async_client.get("/api/v1/subscriptions/me")).status_code == 401
    assert (await async_client.get(f"/api/v1/subscriptions/{sub.id}")).status_code == 401

    # The owner sees it
    res = await async_client.get("/api/v1/subscriptions/me", headers=auth_headers(owner.id, "member"))
    assert res.status_code == 200
    assert [s["id"] for s in res.json()["data"]["subscriptions"]] == [str(sub.id)]
    res = await async_client.get(f"/api/v1/subscriptions/{sub.id}", headers=auth_headers(owner.id, "member"))
    assert res.status_code == 200

    # Another member doesn't
    res = await async_client.get("/api/v1/subscriptions/me", headers=auth_headers(other.id, "member"))
    assert res.json()["data"]["total"] == 0
    res = await async_client.get(f"/api/v1/subscriptions/{sub.id}", headers=auth_headers(other.id, "member"))
    assert res.status_code == 404

    # A creator token is not a member token
    res = await async_client.get("/api/v1/subscriptions/me", headers=auth_headers(owner.id, "creator"))
    assert res.status_code == 403
