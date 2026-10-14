import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_creator
from app.main import app as fastapi_app
from app.modules.community.models import Community
from app.modules.community.repositories import CommunityRepository
from app.modules.telegram_connect.enums import OwnerType
from app.modules.telegram_connect.models import TelegramAccount

BASE = "/api/v1/communities"
CREATOR_ID = uuid.uuid4()


@pytest.fixture
async def client(async_client: AsyncClient, db_session: AsyncSession) -> AsyncClient:
    fastapi_app.dependency_overrides[get_current_creator] = lambda: CREATOR_ID
    # Creating a community requires a connected Telegram account
    db_session.add(
        TelegramAccount(
            owner_type=OwnerType.CREATOR.value,
            owner_id=CREATOR_ID,
            telegram_user_id="987654321",
            phone="+919876543210",
        )
    )
    await db_session.flush()
    return async_client


async def test_create_with_description(client: AsyncClient):
    resp = await client.post(BASE, json={"name": "Java Masters", "description": "Daily Java tips"})
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["name"] == "Java Masters"
    assert data["description"] == "Daily Java tips"
    assert data["telegram_connected"] is False


async def test_create_without_description(client: AsyncClient):
    resp = await client.post(BASE, json={"name": "No Desc"})
    assert resp.status_code == 201
    assert resp.json()["data"]["description"] is None


async def test_blank_description_becomes_null(client: AsyncClient):
    resp = await client.post(BASE, json={"name": "Blank Desc", "description": "   "})
    assert resp.status_code == 201
    assert resp.json()["data"]["description"] is None


async def test_description_too_long_rejected(client: AsyncClient):
    resp = await client.post(BASE, json={"name": "Long Desc", "description": "x" * 501})
    assert resp.status_code == 422


async def test_name_is_trimmed_before_length_check(client: AsyncClient):
    resp = await client.post(BASE, json={"name": "  ab  "})
    assert resp.status_code == 422

    resp = await client.post(BASE, json={"name": "  abc  "})
    assert resp.status_code == 201
    assert resp.json()["data"]["name"] == "abc"


async def test_duplicate_name_rejected(client: AsyncClient):
    assert (await client.post(BASE, json={"name": "Dupe"})).status_code == 201
    resp = await client.post(BASE, json={"name": "Dupe"})
    assert resp.status_code == 409


async def _link_to_chat(db_session: AsyncSession, community_id: str, chat_id: str) -> None:
    await db_session.execute(
        update(Community)
        .where(Community.id == uuid.UUID(community_id))
        .values(telegram_chat_id=chat_id)
    )


async def test_duplicate_race_maps_integrity_error(
    client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    created = (await client.post(BASE, json={"name": "Racy"})).json()["data"]
    await _link_to_chat(db_session, created["id"], "-1001")  # not pending

    # Simulate the race: the pre-check misses the concurrent insert
    async def never_exists(self, *args, **kwargs):
        return False

    monkeypatch.setattr(CommunityRepository, "exists_by_name", never_exists)
    resp = await client.post(BASE, json={"name": "Racy"})
    assert resp.status_code == 409


async def test_update_description_set_keep_and_clear(client: AsyncClient):
    created = (await client.post(BASE, json={"name": "Editable"})).json()["data"]
    url = f"{BASE}/{created['id']}"

    resp = await client.patch(url, json={"name": "Editable", "description": "Now described"})
    assert resp.json()["data"]["description"] == "Now described"

    # Omitted → unchanged
    resp = await client.patch(url, json={"name": "Renamed"})
    assert resp.json()["data"]["name"] == "Renamed"
    assert resp.json()["data"]["description"] == "Now described"

    # Explicit null → cleared
    resp = await client.patch(url, json={"name": "Renamed", "description": None})
    assert resp.json()["data"]["description"] is None


async def test_only_one_community_may_wait_for_telegram(
    client: AsyncClient, db_session: AsyncSession
):
    first = (await client.post(BASE, json={"name": "First"})).json()["data"]

    resp = await client.post(BASE, json={"name": "Second"})
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "PENDING_TELEGRAM_CONNECTION"

    await _link_to_chat(db_session, first["id"], "-1002")
    assert (await client.post(BASE, json={"name": "Second"})).status_code == 201


async def test_reactivating_second_pending_community_is_blocked(
    client: AsyncClient, db_session: AsyncSession
):
    first = (await client.post(BASE, json={"name": "First"})).json()["data"]
    await client.patch(f"{BASE}/{first['id']}/deactivate")

    # Deactivated communities don't count as pending
    second = (await client.post(BASE, json={"name": "Second"})).json()["data"]
    assert second["name"] == "Second"

    resp = await client.patch(f"{BASE}/{first['id']}/activate")
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "PENDING_TELEGRAM_CONNECTION"
