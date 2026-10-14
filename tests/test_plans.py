"""Plans: creators manage plans of their connected communities; members browse them."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers import auth_headers, make_community, make_member

CREATOR_ID = uuid.uuid4()


@pytest.fixture
def creator() -> dict:
    return auth_headers(CREATOR_ID, "creator")


async def _create(client: AsyncClient, community_id, headers: dict, **body) -> dict:
    payload = {"name": "Monthly", "price": "499", "duration_days": 30, **body}
    return (await client.post(
        f"/api/v1/communities/{community_id}/plans", json=payload, headers=headers,
    ))


async def test_creator_creates_multiple_plans(
    async_client: AsyncClient, db_session: AsyncSession, creator: dict
):
    community = await make_community(db_session, CREATOR_ID)

    resp = await _create(async_client, community.id, creator, name="Monthly", price="499.50",
                         description="Billed monthly")
    assert resp.status_code == 201, resp.text
    plan = resp.json()["data"]
    assert plan["price_paise"] == 49950
    assert plan["price"] == "499.50"
    assert plan["currency"] == "INR"
    assert plan["duration_days"] == 30
    assert plan["is_active"] is True

    resp = await _create(async_client, community.id, creator, name="Yearly", price="4999",
                         duration_days=365)
    assert resp.status_code == 201, resp.text

    resp = await async_client.get(f"/api/v1/communities/{community.id}/plans", headers=creator)
    assert [p["name"] for p in resp.json()["data"]] == ["Monthly", "Yearly"]


async def test_plans_need_a_connected_community(
    async_client: AsyncClient, db_session: AsyncSession, creator: dict
):
    community = await make_community(db_session, CREATOR_ID, connected=False)

    resp = await _create(async_client, community.id, creator)
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "COMMUNITY_NOT_CONNECTED"


async def test_other_creator_cannot_touch_plans(
    async_client: AsyncClient, db_session: AsyncSession, creator: dict
):
    community = await make_community(db_session, CREATOR_ID)
    plan = (await _create(async_client, community.id, creator)).json()["data"]
    intruder = auth_headers(uuid.uuid4(), "creator")

    assert (await _create(async_client, community.id, intruder)).status_code == 404
    resp = await async_client.get(f"/api/v1/communities/{community.id}/plans", headers=intruder)
    assert resp.status_code == 404
    resp = await async_client.patch(
        f"/api/v1/plans/{plan['id']}", json={"price": "1"}, headers=intruder,
    )
    assert resp.status_code == 404
    resp = await async_client.patch(f"/api/v1/plans/{plan['id']}/deactivate", headers=intruder)
    assert resp.status_code == 404


async def test_member_token_cannot_manage_plans(
    async_client: AsyncClient, db_session: AsyncSession
):
    community = await make_community(db_session, CREATOR_ID)
    member = auth_headers(uuid.uuid4(), "member")
    assert (await _create(async_client, community.id, member)).status_code in (401, 403)


async def test_duplicate_plan_name_rejected(
    async_client: AsyncClient, db_session: AsyncSession, creator: dict
):
    community = await make_community(db_session, CREATOR_ID)
    await _create(async_client, community.id, creator, name="Monthly")

    resp = await _create(async_client, community.id, creator, name="  Monthly ")
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "DUPLICATE_PLAN_NAME"


@pytest.mark.parametrize("price", ["0", "0.99", "499.999", "-5", "abc"])
async def test_invalid_prices_rejected(
    async_client: AsyncClient, db_session: AsyncSession, creator: dict, price: str
):
    community = await make_community(db_session, CREATOR_ID)
    resp = await _create(async_client, community.id, creator, price=price)
    assert resp.status_code == 422


async def test_update_is_partial(
    async_client: AsyncClient, db_session: AsyncSession, creator: dict
):
    community = await make_community(db_session, CREATOR_ID)
    plan = (await _create(async_client, community.id, creator, description="Old")).json()["data"]

    resp = await async_client.patch(
        f"/api/v1/plans/{plan['id']}", json={"price": "599"}, headers=creator,
    )
    data = resp.json()["data"]
    assert data["price_paise"] == 59900
    assert data["name"] == "Monthly"
    assert data["description"] == "Old"

    resp = await async_client.patch(
        f"/api/v1/plans/{plan['id']}", json={"description": None}, headers=creator,
    )
    assert resp.json()["data"]["description"] is None


async def test_members_see_only_active_plans(
    async_client: AsyncClient, db_session: AsyncSession, creator: dict
):
    community = await make_community(db_session, CREATOR_ID)
    monthly = (await _create(async_client, community.id, creator, name="Monthly")).json()["data"]
    await _create(async_client, community.id, creator, name="Yearly", price="4999")
    await async_client.patch(f"/api/v1/plans/{monthly['id']}/deactivate", headers=creator)

    member = auth_headers((await make_member(db_session)).id, "member")
    resp = await async_client.get(
        f"/api/v1/communities/{community.id}/plans/available", headers=member,
    )
    assert [p["name"] for p in resp.json()["data"]] == ["Yearly"]

    # Creator still sees both
    resp = await async_client.get(f"/api/v1/communities/{community.id}/plans", headers=creator)
    assert len(resp.json()["data"]) == 2

    await async_client.patch(f"/api/v1/plans/{monthly['id']}/activate", headers=creator)
    resp = await async_client.get(
        f"/api/v1/communities/{community.id}/plans/available", headers=member,
    )
    assert [p["name"] for p in resp.json()["data"]] == ["Monthly", "Yearly"]


async def test_unconnected_community_offers_nothing(
    async_client: AsyncClient, db_session: AsyncSession
):
    community = await make_community(db_session, CREATOR_ID, connected=False)
    member = auth_headers(uuid.uuid4(), "member")

    resp = await async_client.get(
        f"/api/v1/communities/{community.id}/plans/available", headers=member,
    )
    assert resp.status_code == 200
    assert resp.json()["data"] == []
