"""Code-free group connection: creator adds the bot as admin → community CONNECTED.

Runs through the real webhook endpoint and the real TelegramDriver; only the
Bot API HTTP layer is faked (getChatMember / sendMessage / getMe).
"""

import itertools
import json
import uuid

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_creator
from app.core.config import get_settings
from app.infrastructure.telegram.telegram_driver import TelegramDriver
from app.main import app as fastapi_app
from app.modules.telegram import constants as tc
from app.modules.telegram.dependencies import get_telegram_client
from app.modules.telegram_connect.dependencies import (
    get_telegram_client as get_connect_telegram_client,
)
from app.modules.telegram_connect.enums import OwnerType
from app.modules.telegram_connect.models import TelegramAccount

BOT_ID = 8000000001
CREATOR_TG_ID = 987654321
STRANGER_TG_ID = 111222333
CHAT_ID = -1001234567890
CREATOR_ID = uuid.uuid4()

ADMIN_RIGHTS = {"can_invite_users": True, "can_restrict_members": True}

_update_ids = itertools.count(1000)


class FakeBotApi:
    """Answers the Bot API calls the driver makes; records sent messages."""

    def __init__(self) -> None:
        # chat_id → getChatMember result for the bot
        self.bot_member: dict[int, dict] = {}
        self.sent: list[dict] = []
        self.fail_get_chat_member = False

    def set_bot(self, chat_id: int, status: str, **rights) -> None:
        self.bot_member[chat_id] = {
            "user": {"id": BOT_ID, "is_bot": True, "first_name": "PulseAccess"},
            "status": status,
            **rights,
        }

    def handle(self, request: httpx.Request) -> httpx.Response:
        method = request.url.path.rsplit("/", 1)[1]
        params = json.loads(request.content or b"{}")
        if method == "getChatMember":
            if self.fail_get_chat_member:
                return self._error(500, "Internal Server Error")
            member = self.bot_member.get(int(params["chat_id"]))
            if member is None:
                return self._error(400, "Bad Request: member not found")
            return self._ok(member)
        if method == "sendMessage":
            self.sent.append(params)
            return self._ok({"message_id": len(self.sent)})
        if method == "getMe":
            return self._ok({"id": BOT_ID, "is_bot": True, "first_name": "PulseAccess"})
        raise AssertionError(f"unexpected Bot API call {method}")

    @staticmethod
    def _ok(result) -> httpx.Response:
        return httpx.Response(200, json={"ok": True, "result": result})

    @staticmethod
    def _error(status: int, description: str) -> httpx.Response:
        return httpx.Response(status, json={"ok": False, "description": description})


@pytest.fixture
def bot_api() -> FakeBotApi:
    return FakeBotApi()


@pytest.fixture
async def client(async_client: AsyncClient, db_session: AsyncSession, bot_api: FakeBotApi):
    driver = TelegramDriver(get_settings().model_copy(update={"TELEGRAM_BOT_TOKEN": "1:TEST"}))
    # Only the driver's HTTP layer is faked; everything above it is real.
    driver._client = httpx.AsyncClient(transport=httpx.MockTransport(bot_api.handle))
    fastapi_app.dependency_overrides[get_telegram_client] = lambda: driver
    fastapi_app.dependency_overrides[get_connect_telegram_client] = lambda: driver
    fastapi_app.dependency_overrides[get_current_creator] = lambda: CREATOR_ID

    db_session.add(TelegramAccount(
        owner_type=OwnerType.CREATOR.value,
        owner_id=CREATOR_ID,
        telegram_user_id=str(CREATOR_TG_ID),
        phone="+919876543210",
    ))
    await db_session.flush()
    return async_client


# ── helpers ─────────────────────────────────────────────────────────────


def _bot_update(
    old: str,
    new: str,
    *,
    actor: int = CREATOR_TG_ID,
    chat_id: int = CHAT_ID,
    chat_type: str = "supergroup",
    update_id: int | None = None,
    **rights,
) -> dict:
    bot = {"id": BOT_ID, "is_bot": True, "first_name": "PulseAccess"}
    return {
        "update_id": update_id if update_id is not None else next(_update_ids),
        "my_chat_member": {
            "chat": {"id": chat_id, "title": "Java Masters", "type": chat_type},
            "from": {"id": actor, "is_bot": False, "first_name": "Naveen"},
            "date": 1760438400,
            "old_chat_member": {"user": bot, "status": old},
            "new_chat_member": {"user": bot, "status": new, **rights},
        },
    }


async def _send(client: AsyncClient, update: dict) -> None:
    resp = await client.post(
        tc.WEBHOOK_PATH,
        json=update,
        headers={"X-Telegram-Bot-Api-Secret-Token": get_settings().TELEGRAM_WEBHOOK_SECRET},
    )
    assert resp.status_code == 200, resp.text


async def _create_community(client: AsyncClient, name: str = "Java Masters") -> str:
    resp = await client.post("/api/v1/communities", json={"name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


async def _status(client: AsyncClient, community_id: str) -> dict:
    resp = await client.get(f"/api/v1/telegram/communities/{community_id}/status")
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


# ── happy paths ─────────────────────────────────────────────────────────


async def test_creator_adds_bot_as_admin_connects(client: AsyncClient, bot_api: FakeBotApi):
    community_id = await _create_community(client)
    bot_api.set_bot(CHAT_ID, "administrator", **ADMIN_RIGHTS)

    await _send(client, _bot_update("left", "administrator", **ADMIN_RIGHTS))

    status = await _status(client, community_id)
    assert status["status"] == "CONNECTED"
    assert status["telegram_chat_id"] == str(CHAT_ID)
    assert status["connected_at"] is not None
    assert bot_api.sent[-1]["chat_id"] == CREATOR_TG_ID
    assert "is now connected" in bot_api.sent[-1]["text"]


async def test_added_as_member_then_promoted(client: AsyncClient, bot_api: FakeBotApi):
    community_id = await _create_community(client)

    bot_api.set_bot(CHAT_ID, "member")
    await _send(client, _bot_update("left", "member"))
    status = await _status(client, community_id)
    assert status["status"] == "NEEDS_ATTENTION"
    assert status["telegram_chat_id"] == str(CHAT_ID)
    assert "need to be an administrator" in bot_api.sent[-1]["text"]

    bot_api.set_bot(CHAT_ID, "administrator", **ADMIN_RIGHTS)
    await _send(client, _bot_update("member", "administrator", **ADMIN_RIGHTS))
    assert (await _status(client, community_id))["status"] == "CONNECTED"


async def test_admin_without_required_rights_needs_attention(
    client: AsyncClient, bot_api: FakeBotApi
):
    community_id = await _create_community(client)
    bot_api.set_bot(CHAT_ID, "administrator", can_invite_users=True, can_restrict_members=False)

    await _send(client, _bot_update("left", "administrator", can_invite_users=True))

    assert (await _status(client, community_id))["status"] == "NEEDS_ATTENTION"


async def test_actual_rights_win_over_update(client: AsyncClient, bot_api: FakeBotApi):
    """A stale update claims admin, but getChatMember says otherwise."""
    community_id = await _create_community(client)
    bot_api.set_bot(CHAT_ID, "member")

    await _send(client, _bot_update("left", "administrator", **ADMIN_RIGHTS))

    assert (await _status(client, community_id))["status"] == "NEEDS_ATTENTION"


async def test_falls_back_to_update_rights_when_telegram_errors(
    client: AsyncClient, bot_api: FakeBotApi
):
    community_id = await _create_community(client)
    bot_api.fail_get_chat_member = True

    await _send(client, _bot_update("left", "administrator", **ADMIN_RIGHTS))

    assert (await _status(client, community_id))["status"] == "CONNECTED"


async def test_channel_connects(client: AsyncClient, bot_api: FakeBotApi):
    community_id = await _create_community(client)
    bot_api.set_bot(CHAT_ID, "administrator", **ADMIN_RIGHTS)

    await _send(client, _bot_update("left", "administrator", chat_type="channel", **ADMIN_RIGHTS))

    assert (await _status(client, community_id))["status"] == "CONNECTED"


# ── who / which community ───────────────────────────────────────────────


async def test_bot_added_by_non_creator_is_ignored(client: AsyncClient, bot_api: FakeBotApi):
    community_id = await _create_community(client)
    bot_api.set_bot(CHAT_ID, "administrator", **ADMIN_RIGHTS)

    await _send(client, _bot_update("left", "administrator", actor=STRANGER_TG_ID, **ADMIN_RIGHTS))

    status = await _status(client, community_id)
    assert status["telegram_chat_id"] is None
    assert status["status"] == "NOT_CONNECTED"
    assert bot_api.sent == []


async def test_creator_without_pending_community_is_told(
    client: AsyncClient, bot_api: FakeBotApi
):
    bot_api.set_bot(CHAT_ID, "administrator", **ADMIN_RIGHTS)

    await _send(client, _bot_update("left", "administrator", **ADMIN_RIGHTS))

    assert bot_api.sent[-1]["chat_id"] == CREATOR_TG_ID
    assert "no PulseAccess community waiting" in bot_api.sent[-1]["text"]


async def test_second_group_does_not_steal_connected_community(
    client: AsyncClient, bot_api: FakeBotApi
):
    community_id = await _create_community(client)
    bot_api.set_bot(CHAT_ID, "administrator", **ADMIN_RIGHTS)
    await _send(client, _bot_update("left", "administrator", **ADMIN_RIGHTS))

    other_chat = -1009999999999
    bot_api.set_bot(other_chat, "administrator", **ADMIN_RIGHTS)
    await _send(client, _bot_update("left", "administrator", chat_id=other_chat, **ADMIN_RIGHTS))

    assert (await _status(client, community_id))["telegram_chat_id"] == str(CHAT_ID)


async def test_private_chat_updates_are_ignored(client: AsyncClient, bot_api: FakeBotApi):
    community_id = await _create_community(client)

    await _send(client, _bot_update("member", "kicked", chat_id=CREATOR_TG_ID, chat_type="private"))

    assert (await _status(client, community_id))["status"] == "NOT_CONNECTED"


# ── after connecting ────────────────────────────────────────────────────


async def test_bot_removed_needs_attention(client: AsyncClient, bot_api: FakeBotApi):
    community_id = await _create_community(client)
    bot_api.set_bot(CHAT_ID, "administrator", **ADMIN_RIGHTS)
    await _send(client, _bot_update("left", "administrator", **ADMIN_RIGHTS))

    await _send(client, _bot_update("administrator", "kicked"))

    status = await _status(client, community_id)
    assert status["status"] == "NEEDS_ATTENTION"
    assert status["telegram_chat_id"] == str(CHAT_ID)  # re-adding reconnects
    assert "I was removed" in bot_api.sent[-1]["text"]

    await _send(client, _bot_update("left", "administrator", **ADMIN_RIGHTS))
    assert (await _status(client, community_id))["status"] == "CONNECTED"


async def test_group_upgrade_moves_chat_id(client: AsyncClient, bot_api: FakeBotApi):
    old_chat, new_chat = -4512345678, -1004512345678
    community_id = await _create_community(client)
    bot_api.set_bot(old_chat, "administrator", **ADMIN_RIGHTS)
    await _send(client, _bot_update("left", "administrator", chat_id=old_chat,
                                    chat_type="group", **ADMIN_RIGHTS))

    bot_api.set_bot(new_chat, "administrator", **ADMIN_RIGHTS)
    await _send(client, {
        "update_id": next(_update_ids),
        "message": {
            "message_id": 7,
            "chat": {"id": old_chat, "title": "Java Masters", "type": "group"},
            "date": 1760438500,
            "migrate_to_chat_id": new_chat,
        },
    })

    status = await _status(client, community_id)
    assert status["telegram_chat_id"] == str(new_chat)
    assert status["status"] == "CONNECTED"


async def test_duplicate_update_is_processed_once(client: AsyncClient, bot_api: FakeBotApi):
    community_id = await _create_community(client)
    bot_api.set_bot(CHAT_ID, "administrator", **ADMIN_RIGHTS)
    update = _bot_update("left", "administrator", update_id=42, **ADMIN_RIGHTS)

    await _send(client, update)
    await _send(client, update)

    assert (await _status(client, community_id))["status"] == "CONNECTED"
    assert len(bot_api.sent) == 1  # "connected" message sent once


async def test_connected_community_allows_creating_the_next(
    client: AsyncClient, bot_api: FakeBotApi
):
    await _create_community(client, "First")
    resp = await client.post("/api/v1/communities", json={"name": "Second"})
    assert resp.json()["error_code"] == "PENDING_TELEGRAM_CONNECTION"

    bot_api.set_bot(CHAT_ID, "administrator", **ADMIN_RIGHTS)
    await _send(client, _bot_update("left", "administrator", **ADMIN_RIGHTS))

    await _create_community(client, "Second")
