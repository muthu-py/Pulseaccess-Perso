import uuid

import pytest
from httpx import AsyncClient

from app.api.dependencies import get_current_creator
from app.main import app as fastapi_app
from app.modules.community.repositories import CommunityRepository

BASE = "/api/v1/communities"
CREATOR_ID = uuid.uuid4()


@pytest.fixture
async def client(async_client: AsyncClient) -> AsyncClient:
    fastapi_app.dependency_overrides[get_current_creator] = lambda: CREATOR_ID
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


async def test_duplicate_race_maps_integrity_error(client: AsyncClient, monkeypatch):
    assert (await client.post(BASE, json={"name": "Racy"})).status_code == 201

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
