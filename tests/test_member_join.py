"""Members getting into (and out of) a community's Telegram group.

Join link → join request → bot approves only members with an active plan.
Payment → DM with a "Join group" button. Plan ends → removed once.
Telegram is the stub (records approve / decline / messages / invite links).
"""

import itertools
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.infrastructure.telegram.telegram_stub import TelegramStub
from app.main import app as fastapi_app
from app.modules.member.enums import MembershipStatus
from app.modules.member.models import CommunityMember
from app.modules.payment.dependencies import get_razorpay_client
from app.modules.plan.models import Plan
from app.modules.subscription.enums import SubscriptionStatus
from app.modules.subscription.models import Subscription
from app.modules.telegram import constants as tc
from app.modules.telegram.dependencies import get_telegram_client
from app.modules.telegram.enums import TelegramOperationType
from app.modules.telegram.models import TelegramOperation
from app.modules.telegram_connect.models import TelegramAccount
from app.workers.subscription_expiry_worker import run_expiry_cycle
from tests.helpers import auth_headers, make_community, make_member

_update_ids = itertools.count(50_000)


@pytest.fixture
def stub() -> TelegramStub:
    return TelegramStub()


@pytest.fixture
def client(async_client: AsyncClient, stub: TelegramStub) -> AsyncClient:
    fastapi_app.dependency_overrides[get_telegram_client] = lambda: stub
    return async_client


@pytest.fixture
async def setup(db_session: AsyncSession):
    """A connected community with a 30-day plan, and a member with Telegram."""
    community = await make_community(db_session, uuid.uuid4())
    plan = Plan(community_id=community.id, name="Monthly", price_paise=49900, duration_days=30)
    db_session.add(plan)
    member = await make_member(db_session)
    await db_session.flush()
    return {
        "community": community,
        "plan": plan,
        "member": member,
        "tg_id": int(await _telegram_id(db_session, member.id)),
        "headers": auth_headers(member.id, "member"),
    }


# ── helpers ─────────────────────────────────────────────────────────────


async def _telegram_id(db: AsyncSession, member_id) -> str:
    result = await db.execute(
        select(TelegramAccount.telegram_user_id).where(TelegramAccount.owner_id == member_id)
    )
    return result.scalar_one()


async def _subscribe(db: AsyncSession, member_id, plan_id, *, days: float = 30) -> Subscription:
    now = datetime.now(timezone.utc)
    sub = Subscription(
        member_id=member_id,
        plan_id=plan_id,
        status=SubscriptionStatus.ACTIVE.value,
        starts_at=now - timedelta(days=1),
        ends_at=now + timedelta(days=days),
    )
    db.add(sub)
    await db.flush()
    return sub


async def _membership(db: AsyncSession, member_id, community_id) -> CommunityMember | None:
    result = await db.execute(select(CommunityMember).where(
        CommunityMember.member_id == member_id,
        CommunityMember.community_id == community_id,
    ))
    return result.scalar_one_or_none()


async def _send(client: AsyncClient, update: dict) -> None:
    update = {"update_id": next(_update_ids), **update}
    resp = await client.post(
        tc.WEBHOOK_PATH,
        json=update,
        headers={"X-Telegram-Bot-Api-Secret-Token": get_settings().TELEGRAM_WEBHOOK_SECRET},
    )
    assert resp.status_code == 200, resp.text


def _join_request(chat_id: str, user_id: int) -> dict:
    return {"chat_join_request": {
        "chat": {"id": int(chat_id), "type": "supergroup", "title": "Java Masters"},
        "from": {"id": user_id, "is_bot": False, "first_name": "Muthu"},
        "user_chat_id": user_id,
        "date": 1760438400,
        "invite_link": {"invite_link": "https://t.me/+abc", "creates_join_request": True},
    }}


def _chat_member(chat_id: str, user_id: int, status: str) -> dict:
    user = {"id": user_id, "is_bot": False, "first_name": "Muthu"}
    return {"chat_member": {
        "chat": {"id": int(chat_id), "type": "supergroup", "title": "Java Masters"},
        "from": user,
        "date": 1760438400,
        "old_chat_member": {"user": user, "status": "left"},
        "new_chat_member": {"user": user, "status": status},
    }}


async def _invite(client: AsyncClient, setup: dict):
    return await client.post(
        f"/api/v1/telegram/communities/{setup['community'].id}/invite",
        headers=setup["headers"],
    )


# ── join link from the site ─────────────────────────────────────────────


async def test_join_link_needs_an_active_plan(client: AsyncClient, setup, stub):
    resp = await _invite(client, setup)
    assert resp.status_code == 403
    assert resp.json()["error_code"] == "SUBSCRIPTION_INACTIVE"
    assert stub.invite_links == []


async def test_join_link_for_paying_member(client: AsyncClient, db_session, setup, stub):
    await _subscribe(db_session, setup["member"].id, setup["plan"].id)

    resp = await _invite(client, setup)
    assert resp.status_code == 200, resp.text
    link = resp.json()["data"]["invite_link"]

    # One shared join-request link per community, created once and reused
    assert len(stub.invite_links) == 1
    assert stub.invite_links[0]["creates_join_request"] is True
    assert stub.invite_links[0]["member_limit"] is None
    assert (await _invite(client, setup)).json()["data"]["invite_link"] == link
    assert len(stub.invite_links) == 1
    assert setup["community"].telegram_join_link == link

    membership = await _membership(db_session, setup["member"].id, setup["community"].id)
    assert membership.status == MembershipStatus.PAID_NOT_JOINED.value


async def test_plan_in_another_community_does_not_count(client: AsyncClient, db_session, setup):
    other = await make_community(db_session, uuid.uuid4(), name="Other")
    other_plan = Plan(community_id=other.id, name="Monthly", price_paise=100, duration_days=30)
    db_session.add(other_plan)
    await db_session.flush()
    await _subscribe(db_session, setup["member"].id, other_plan.id)

    assert (await _invite(client, setup)).status_code == 403


async def test_expired_plan_gets_no_link(client: AsyncClient, db_session, setup):
    await _subscribe(db_session, setup["member"].id, setup["plan"].id, days=-1)
    assert (await _invite(client, setup)).status_code == 403


async def test_unconnected_community_gets_no_link(client: AsyncClient, db_session, setup):
    community = await make_community(db_session, uuid.uuid4(), name="Pending", connected=False)
    resp = await client.post(
        f"/api/v1/telegram/communities/{community.id}/invite", headers=setup["headers"],
    )
    assert resp.status_code == 409


async def test_creator_token_cannot_get_a_join_link(client: AsyncClient, setup):
    resp = await client.post(
        f"/api/v1/telegram/communities/{setup['community'].id}/invite",
        headers=auth_headers(setup["member"].id, "creator"),
    )
    assert resp.status_code == 403


# ── join requests ───────────────────────────────────────────────────────


async def test_paying_member_is_approved(client: AsyncClient, db_session, setup, stub):
    await _subscribe(db_session, setup["member"].id, setup["plan"].id)
    chat_id = setup["community"].telegram_chat_id

    await _send(client, _join_request(chat_id, setup["tg_id"]))

    assert stub.approved == [(chat_id, setup["tg_id"])]
    assert stub.declined == []
    membership = await _membership(db_session, setup["member"].id, setup["community"].id)
    assert membership.status == MembershipStatus.JOINED.value
    assert membership.group_joined_at is not None


async def test_stranger_is_declined_and_told_why(client: AsyncClient, setup, stub):
    chat_id = setup["community"].telegram_chat_id

    await _send(client, _join_request(chat_id, 555000111))

    assert stub.approved == []
    assert stub.declined == [(chat_id, 555000111)]
    assert stub.sent_messages[-1]["chat_id"] == 555000111
    assert "no active plan" in stub.sent_messages[-1]["text"]


async def test_member_without_plan_is_declined(client: AsyncClient, db_session, setup, stub):
    await _subscribe(db_session, setup["member"].id, setup["plan"].id, days=-1)
    chat_id = setup["community"].telegram_chat_id

    await _send(client, _join_request(chat_id, setup["tg_id"]))

    assert stub.declined == [(chat_id, setup["tg_id"])]
    assert await _membership(db_session, setup["member"].id, setup["community"].id) is None


async def test_requests_to_other_groups_are_left_alone(client: AsyncClient, setup, stub):
    await _send(client, _join_request("-1009999999999", setup["tg_id"]))
    assert stub.approved == [] and stub.declined == [] and stub.sent_messages == []


# ── payment → DM with the join button ───────────────────────────────────


@pytest.fixture
def razorpay_client(client: AsyncClient):
    import httpx

    from app.infrastructure.razorpay.razorpay_driver import RazorpayDriver
    from tests.test_payment_links import WEBHOOK_SECRET, FakeRazorpay

    settings = get_settings().model_copy(update={
        "RAZORPAY_KEY_ID": "rzp_test_key",
        "RAZORPAY_KEY_SECRET": "rzp_test_secret",
        "RAZORPAY_WEBHOOK_SECRET": WEBHOOK_SECRET,
    })
    driver = RazorpayDriver(settings, transport=httpx.MockTransport(FakeRazorpay().handle))
    fastapi_app.dependency_overrides[get_razorpay_client] = lambda: driver
    return client


async def _pay(client: AsyncClient, db: AsyncSession, setup: dict) -> None:
    """Buy the plan and deliver Razorpay's payment_link.paid webhook."""
    from app.modules.payment.models import PaymentOrder
    from tests.test_payment_links import _paid_event, _webhook

    resp = await client.post(f"/api/v1/plans/{setup['plan'].id}/payment-link", headers=setup["headers"])
    assert resp.status_code == 201, resp.text
    order = await db.get(PaymentOrder, uuid.UUID(resp.json()["data"]["id"]))
    await _webhook(client, _paid_event(order.razorpay_payment_link_id, order.amount_paise))


async def test_payment_sends_join_button(razorpay_client: AsyncClient, db_session, setup, stub):
    stub.member_status[setup["tg_id"]] = "left"  # not in the group yet
    await _pay(razorpay_client, db_session, setup)

    dm = stub.sent_messages[-1]
    assert dm["chat_id"] == setup["tg_id"]
    assert "Payment received" in dm["text"]
    button = dm["reply_markup"]["inline_keyboard"][0][0]
    assert button["url"] == setup["community"].telegram_join_link
    assert stub.invite_links[0]["creates_join_request"] is True

    membership = await _membership(db_session, setup["member"].id, setup["community"].id)
    assert membership.status == MembershipStatus.PAID_NOT_JOINED.value

    # The DM'd link works: the bot approves the request
    await _send(razorpay_client, _join_request(setup["community"].telegram_chat_id, setup["tg_id"]))
    assert stub.approved == [(setup["community"].telegram_chat_id, setup["tg_id"])]


async def test_payment_when_already_in_group(razorpay_client: AsyncClient, db_session, setup, stub):
    stub.member_status[setup["tg_id"]] = "member"  # joined before PulseAccess tracked it
    await _pay(razorpay_client, db_session, setup)

    assert "extended" in stub.sent_messages[-1]["text"]
    assert stub.sent_messages[-1]["reply_markup"] is None
    membership = await _membership(db_session, setup["member"].id, setup["community"].id)
    assert membership.status == MembershipStatus.JOINED.value


# ── group membership events ─────────────────────────────────────────────


async def test_leaving_and_rejoining_is_tracked(client: AsyncClient, db_session, setup):
    await _subscribe(db_session, setup["member"].id, setup["plan"].id)
    chat_id = setup["community"].telegram_chat_id

    await _send(client, _chat_member(chat_id, setup["tg_id"], "member"))
    membership = await _membership(db_session, setup["member"].id, setup["community"].id)
    assert membership.status == MembershipStatus.JOINED.value

    await _send(client, _chat_member(chat_id, setup["tg_id"], "left"))
    await db_session.refresh(membership)
    assert membership.status == MembershipStatus.LEFT.value


async def test_people_without_a_plan_are_left_alone(client: AsyncClient, db_session, setup):
    await _send(client, _chat_member(setup["community"].telegram_chat_id, setup["tg_id"], "member"))
    assert await _membership(db_session, setup["member"].id, setup["community"].id) is None


# ── plan ends → removed once ────────────────────────────────────────────


async def _removals(db: AsyncSession) -> list[TelegramOperation]:
    result = await db.execute(select(TelegramOperation).where(
        TelegramOperation.operation_type == TelegramOperationType.REMOVE_MEMBER.value,
    ))
    return list(result.scalars().all())


async def test_expired_plan_removes_member_once(client: AsyncClient, db_session, setup):
    sub = await _subscribe(db_session, setup["member"].id, setup["plan"].id, days=-0.01)
    await _send(client, _chat_member(setup["community"].telegram_chat_id, setup["tg_id"], "member"))

    expired, queued = await run_expiry_cycle(db_session)
    assert (expired, queued) == (1, 1)
    await db_session.refresh(sub)
    assert sub.status == SubscriptionStatus.EXPIRED.value
    assert sub.access_revoked_at is not None
    ops = await _removals(db_session)
    assert [(op.community_id, op.member_id) for op in ops] == [
        (setup["community"].id, setup["member"].id),
    ]
    membership = await _membership(db_session, setup["member"].id, setup["community"].id)
    assert membership.status == MembershipStatus.REMOVED.value

    # Next cycles do nothing more
    assert await run_expiry_cycle(db_session) == (0, 0)
    assert len(await _removals(db_session)) == 1

    # Our own ban / unban echoes back as kicked / left: still REMOVED
    await _send(client, _chat_member(setup["community"].telegram_chat_id, setup["tg_id"], "kicked"))
    await db_session.refresh(membership)
    assert membership.status == MembershipStatus.REMOVED.value


async def test_another_active_plan_keeps_member_in(client: AsyncClient, db_session, setup):
    yearly = Plan(community_id=setup["community"].id, name="Yearly", price_paise=99900, duration_days=365)
    db_session.add(yearly)
    await db_session.flush()
    await _subscribe(db_session, setup["member"].id, setup["plan"].id, days=-0.01)
    await _subscribe(db_session, setup["member"].id, yearly.id, days=300)
    await _send(client, _chat_member(setup["community"].telegram_chat_id, setup["tg_id"], "member"))

    assert await run_expiry_cycle(db_session) == (1, 0)
    assert await _removals(db_session) == []
    membership = await _membership(db_session, setup["member"].id, setup["community"].id)
    assert membership.status == MembershipStatus.JOINED.value


async def test_renewing_after_removal_lets_member_back(client: AsyncClient, db_session, setup, stub):
    await _subscribe(db_session, setup["member"].id, setup["plan"].id, days=-0.01)
    await run_expiry_cycle(db_session)

    await _subscribe(db_session, setup["member"].id, setup["plan"].id)  # paid again
    await _send(client, _join_request(setup["community"].telegram_chat_id, setup["tg_id"]))

    assert stub.approved == [(setup["community"].telegram_chat_id, setup["tg_id"])]
    membership = await _membership(db_session, setup["member"].id, setup["community"].id)
    assert membership.status == MembershipStatus.JOINED.value
