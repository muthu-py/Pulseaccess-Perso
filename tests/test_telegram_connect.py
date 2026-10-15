"""Connect Telegram: member/creator login roles, bot linking flow and guards."""

import itertools
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_email_service
from app.core.config import get_settings
from app.infrastructure.security.jwt_service import JWTService
from app.infrastructure.telegram.telegram_stub import TelegramStub
from app.main import app as fastapi_app
from app.modules.auth.models import Creator
from app.modules.telegram_connect.dependencies import get_telegram_client

MEMBER_PHONE = "+919876543210"
TG_USER_ID = 555000111

# The webhook skips repeated update_ids, so every test update needs its own.
_update_ids = itertools.count(1)


class FakeEmailService:
    def __init__(self) -> None:
        self.last_otp: str | None = None

    async def send_login_otp(self, to_email: str, otp_code: str, creator_name: str) -> None:
        self.last_otp = otp_code


@pytest.fixture
def stub() -> TelegramStub:
    return TelegramStub()


@pytest.fixture
def email() -> FakeEmailService:
    return FakeEmailService()


@pytest.fixture(autouse=True)
def _overrides(async_client: AsyncClient, stub: TelegramStub, email: FakeEmailService):
    fastapi_app.dependency_overrides[get_telegram_client] = lambda: stub
    fastapi_app.dependency_overrides[get_email_service] = lambda: email
    yield


def _webhook_headers() -> dict:
    return {"X-Telegram-Bot-Api-Secret-Token": get_settings().TELEGRAM_WEBHOOK_SECRET}


def _private_message(user_id: int = TG_USER_ID, **fields) -> dict:
    return {
        "update_id": next(_update_ids),
        "message": {
            "message_id": 1,
            "from": {"id": user_id, "is_bot": False, "first_name": "Test", "username": "tester"},
            "chat": {"id": user_id, "type": "private"},
            **fields,
        },
    }


def _contact(phone: str, user_id: int = TG_USER_ID, owner_user_id: int | None = None) -> dict:
    return _private_message(
        user_id=user_id,
        contact={
            "phone_number": phone,
            "first_name": "Test",
            "user_id": owner_user_id if owner_user_id is not None else user_id,
        },
    )


async def _send(client: AsyncClient, update: dict) -> None:
    res = await client.post("/api/v1/webhooks/telegram", json=update, headers=_webhook_headers())
    assert res.status_code == 200


async def _register_and_login_member(
    client: AsyncClient,
    email: FakeEmailService,
    phone: str = MEMBER_PHONE,
    address: str = "member@example.com",
) -> dict:
    res = await client.post(
        "/api/v1/members/register",
        json={"name": "Member", "email": address, "phone": phone},
    )
    assert res.status_code == 201, res.text
    await client.post("/api/v1/members/request-otp", json={"email": address})
    res = await client.post(
        "/api/v1/members/verify-otp",
        json={"email": address, "otp_code": email.last_otp},
    )
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['data']['access_token']}"}


async def _creator_headers(db_session: AsyncSession, phone: str | None) -> dict:
    creator = Creator(name="Creator", username=f"c_{uuid.uuid4().hex[:8]}",
                      email=f"{uuid.uuid4().hex[:8]}@example.com", phone=phone)
    db_session.add(creator)
    await db_session.commit()
    token = JWTService(get_settings()).create_access_token(
        subject=str(creator.id), extra_claims={"role": "creator"},
    )
    return {"Authorization": f"Bearer {token}"}


async def _start_link(client: AsyncClient, path: str, headers: dict) -> str:
    res = await client.post(f"/api/v1/telegram/connect/{path}", headers=headers)
    assert res.status_code == 200, res.text
    link = res.json()["data"]["telegram_link"]
    assert "?start=" in link
    return link.split("?start=", 1)[1]


# ======================================================================
# Member flow
# ======================================================================


async def test_member_connects_telegram_then_can_pay(
    async_client: AsyncClient, db_session: AsyncSession, stub: TelegramStub, email,
):
    headers = await _register_and_login_member(async_client, email)

    # Not connected yet → paying is blocked
    res = await async_client.post(
        f"/api/v1/plans/{uuid.uuid4()}/payment-link", headers=headers,
    )
    assert res.status_code == 403
    assert res.json()["error_code"] == "TELEGRAM_NOT_CONNECTED"

    token = await _start_link(async_client, "member", headers)

    # Tap Start → bot asks for the phone with a request_contact button
    await _send(async_client, _private_message(text=f"/start {token}"))
    keyboard = stub.sent_messages[-1]["reply_markup"]["keyboard"]
    assert keyboard[0][0]["request_contact"] is True

    # Share own phone (Telegram sends it without '+')
    await _send(async_client, _contact("919876543210"))
    assert "Connected" in stub.sent_messages[-1]["text"]

    res = await async_client.get("/api/v1/telegram/connect/member", headers=headers)
    data = res.json()["data"]
    assert data["connected"] is True
    assert data["telegram_username"] == "tester"

    res = await async_client.get("/api/v1/members/me", headers=headers)
    assert res.json()["data"]["telegram_connected"] is True

    # Guard now lets the member through (plan doesn't exist → 404, not 403)
    res = await async_client.post(
        f"/api/v1/plans/{uuid.uuid4()}/payment-link", headers=headers,
    )
    assert res.status_code == 404


async def test_phone_mismatch_is_rejected(async_client: AsyncClient, stub: TelegramStub, email):
    headers = await _register_and_login_member(async_client, email)
    token = await _start_link(async_client, "member", headers)

    await _send(async_client, _private_message(text=f"/start {token}"))
    await _send(async_client, _contact("+911111111111"))

    assert "doesn't match" in stub.sent_messages[-1]["text"]
    res = await async_client.get("/api/v1/telegram/connect/member", headers=headers)
    assert res.json()["data"]["connected"] is False


async def test_forwarded_contact_is_rejected(async_client: AsyncClient, stub: TelegramStub, email):
    headers = await _register_and_login_member(async_client, email)
    token = await _start_link(async_client, "member", headers)

    await _send(async_client, _private_message(text=f"/start {token}"))
    # Correct phone, but the contact card belongs to a different Telegram user
    await _send(async_client, _contact("919876543210", owner_user_id=999))

    assert "your own phone number" in stub.sent_messages[-1]["text"]
    res = await async_client.get("/api/v1/telegram/connect/member", headers=headers)
    assert res.json()["data"]["connected"] is False


async def test_link_cannot_be_used_by_another_telegram_user(
    async_client: AsyncClient, stub: TelegramStub, email,
):
    headers = await _register_and_login_member(async_client, email)
    token = await _start_link(async_client, "member", headers)

    await _send(async_client, _private_message(text=f"/start {token}"))
    await _send(async_client, _private_message(user_id=777, text=f"/start {token}"))

    assert "expired or was already used" in stub.sent_messages[-1]["text"]


async def test_unknown_token_and_plain_start(async_client: AsyncClient, stub: TelegramStub):
    await _send(async_client, _private_message(text="/start not-a-real-token"))
    assert "expired or was already used" in stub.sent_messages[-1]["text"]

    await _send(async_client, _private_message(text="/start"))
    assert "Connect Telegram" in stub.sent_messages[-1]["text"]


async def test_group_messages_are_ignored(async_client: AsyncClient, stub: TelegramStub):
    update = _private_message(text="/start hello")
    update["message"]["chat"] = {"id": -100123, "type": "supergroup"}
    await _send(async_client, update)
    assert stub.sent_messages == []


async def test_telegram_account_cannot_link_two_members(
    async_client: AsyncClient, stub: TelegramStub, email,
):
    first = await _register_and_login_member(async_client, email)
    token = await _start_link(async_client, "member", first)
    await _send(async_client, _private_message(text=f"/start {token}"))
    await _send(async_client, _contact("919876543210"))

    second = await _register_and_login_member(
        async_client, email, phone="+919000000000", address="second@example.com",
    )
    token = await _start_link(async_client, "member", second)
    await _send(async_client, _private_message(text=f"/start {token}"))
    await _send(async_client, _contact("919000000000"))

    assert "already connected to another" in stub.sent_messages[-1]["text"]


async def test_member_registration_rejects_duplicates_and_bad_phone(async_client: AsyncClient, email):
    await _register_and_login_member(async_client, email)
    res = await async_client.post(
        "/api/v1/members/register",
        json={"name": "X", "email": "other@example.com", "phone": "+91 98765-43210"},
    )
    assert res.status_code == 409

    res = await async_client.post(
        "/api/v1/members/register",
        json={"name": "X", "email": "third@example.com", "phone": "9876543210"},
    )
    assert res.status_code == 422


# ======================================================================
# Creator flow and login separation
# ======================================================================


async def test_creator_must_connect_before_creating_community(
    async_client: AsyncClient, db_session: AsyncSession, stub: TelegramStub,
):
    headers = await _creator_headers(db_session, phone=None)

    res = await async_client.post("/api/v1/communities", json={"name": "My Group"}, headers=headers)
    assert res.json()["error_code"] == "TELEGRAM_NOT_CONNECTED"

    # No phone yet → can't start connecting
    res = await async_client.post("/api/v1/telegram/connect/creator", headers=headers)
    assert res.json()["error_code"] == "PHONE_REQUIRED"

    res = await async_client.put(
        "/api/v1/auth/phone", json={"phone": "+918888888888"}, headers=headers,
    )
    assert res.status_code == 200, res.text

    token = await _start_link(async_client, "creator", headers)
    await _send(async_client, _private_message(text=f"/start {token}"))
    await _send(async_client, _contact("918888888888"))
    assert "Connected" in stub.sent_messages[-1]["text"]

    res = await async_client.post("/api/v1/communities", json={"name": "My Group"}, headers=headers)
    assert res.status_code == 201, res.text


async def test_same_telegram_account_can_be_creator_and_member(
    async_client: AsyncClient, db_session: AsyncSession, stub: TelegramStub, email,
):
    creator = await _creator_headers(db_session, phone=MEMBER_PHONE)
    token = await _start_link(async_client, "creator", creator)
    await _send(async_client, _private_message(text=f"/start {token}"))
    await _send(async_client, _contact("919876543210"))

    member = await _register_and_login_member(async_client, email)
    token = await _start_link(async_client, "member", member)
    await _send(async_client, _private_message(text=f"/start {token}"))
    await _send(async_client, _contact("919876543210"))
    assert "Connected" in stub.sent_messages[-1]["text"]


async def test_logins_are_separate(async_client: AsyncClient, db_session: AsyncSession, email):
    member = await _register_and_login_member(async_client, email)
    creator = await _creator_headers(db_session, phone=None)

    res = await async_client.post("/api/v1/communities", json={"name": "Nope"}, headers=member)
    assert res.status_code == 403

    res = await async_client.get("/api/v1/members/me", headers=creator)
    assert res.status_code == 403
