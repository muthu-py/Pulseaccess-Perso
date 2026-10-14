"""Creator removes a member whose plan has ended (DELETE .../members/{member_id})."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.telegram.telegram_exceptions import (
    TelegramPermissionException,
    TelegramTimeoutException,
)
from app.infrastructure.telegram.telegram_stub import TelegramStub
from app.main import app as fastapi_app
from app.modules.member.enums import MembershipStatus
from app.modules.member.models import CommunityMember
from app.modules.plan.models import Plan
from app.modules.subscription.enums import SubscriptionStatus
from app.modules.subscription.models import Subscription
from app.modules.telegram import constants as tc
from app.modules.telegram.dependencies import get_telegram_client
from app.modules.telegram.enums import TelegramOperationType
from app.modules.telegram.models import TelegramOperation
from app.modules.telegram.repositories import TelegramRepository
from app.modules.telegram_connect.models import TelegramAccount
from tests.helpers import auth_headers, make_community, make_member


class BanStub(TelegramStub):
    def __init__(self) -> None:
        super().__init__()
        self.ban_error: Exception | None = None

    async def ban_member(self, chat_id, user_id):
        if self.ban_error is not None:
            raise self.ban_error
        return await super().ban_member(chat_id, user_id)


@pytest.fixture
def stub() -> BanStub:
    return BanStub()


@pytest.fixture
def client(async_client: AsyncClient, stub: BanStub) -> AsyncClient:
    fastapi_app.dependency_overrides[get_telegram_client] = lambda: stub
    return async_client


@pytest.fixture
async def setup(db_session: AsyncSession):
    """A member in the group whose plan ended yesterday (not yet expired by the daily check)."""
    creator_id = uuid.uuid4()
    community = await make_community(db_session, creator_id)
    plan = Plan(community_id=community.id, name="Monthly", price_paise=49900, duration_days=30)
    db_session.add(plan)
    member = await make_member(db_session)
    await db_session.flush()
    now = datetime.now(timezone.utc)
    db_session.add(Subscription(
        member_id=member.id,
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE.value,
        starts_at=now - timedelta(days=31),
        ends_at=now - timedelta(days=1),
    ))
    await TelegramRepository(db_session).set_membership_status(
        member.id, community.id, MembershipStatus.JOINED,
    )
    tg_id = (await db_session.execute(
        select(TelegramAccount.telegram_user_id).where(TelegramAccount.owner_id == member.id)
    )).scalar_one()
    await db_session.commit()
    return {
        "community": community,
        "plan": plan,
        "member": member,
        "tg_id": int(tg_id),
        "headers": auth_headers(creator_id, "creator"),
    }


def _url(setup) -> str:
    return f"/api/v1/telegram/communities/{setup['community'].id}/members/{setup['member'].id}"


async def _membership_status(db: AsyncSession, setup) -> str:
    result = await db.execute(select(CommunityMember.status).where(
        CommunityMember.member_id == setup["member"].id,
        CommunityMember.community_id == setup["community"].id,
    ))
    return result.scalar_one()


async def _queued_removals(db: AsyncSession) -> int:
    result = await db.execute(select(TelegramOperation).where(
        TelegramOperation.operation_type == TelegramOperationType.REMOVE_MEMBER.value,
    ))
    return len(result.scalars().all())


async def test_removes_expired_member_now(client, db_session, setup, stub):
    resp = await client.delete(_url(setup), headers=setup["headers"])

    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["telegram_removal"] == "DONE"
    assert stub.banned == [(setup["community"].telegram_chat_id, setup["tg_id"])]
    assert await _membership_status(db_session, setup) == MembershipStatus.REMOVED.value
    assert stub.sent_messages[-1]["text"] == tc.MSG_ACCESS_ENDED.format(
        community=setup["community"].name,
    )


async def test_second_call_is_a_no_op(client, setup, stub):
    await client.delete(_url(setup), headers=setup["headers"])
    resp = await client.delete(_url(setup), headers=setup["headers"])
    assert resp.status_code == 200
    assert resp.json()["data"]["telegram_removal"] == "ALREADY_REMOVED"
    assert len(stub.banned) == 1


async def test_active_plan_cannot_be_removed(client, db_session, setup, stub):
    now = datetime.now(timezone.utc)
    db_session.add(Subscription(
        member_id=setup["member"].id,
        plan_id=setup["plan"].id,
        status=SubscriptionStatus.ACTIVE.value,
        starts_at=now,
        ends_at=now + timedelta(days=30),
    ))
    await db_session.commit()

    resp = await client.delete(_url(setup), headers=setup["headers"])

    assert resp.status_code == 409
    assert stub.banned == []
    assert await _membership_status(db_session, setup) == MembershipStatus.JOINED.value


async def test_telegram_down_queues_the_removal(client, db_session, setup, stub):
    stub.ban_error = TelegramTimeoutException()
    resp = await client.delete(_url(setup), headers=setup["headers"])
    assert resp.status_code == 200
    assert resp.json()["data"]["telegram_removal"] == "QUEUED"
    assert await _queued_removals(db_session) == 1
    assert await _membership_status(db_session, setup) == MembershipStatus.REMOVED.value


async def test_bot_without_rights_reports_it(client, db_session, setup, stub):
    stub.ban_error = TelegramPermissionException("not enough rights")
    resp = await client.delete(_url(setup), headers=setup["headers"])
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "BOT_CANNOT_REMOVE_MEMBER"
    assert await _membership_status(db_session, setup) == MembershipStatus.JOINED.value


async def test_other_creator_is_refused(client, setup):
    resp = await client.delete(_url(setup), headers=auth_headers(uuid.uuid4(), "creator"))
    assert resp.status_code == 403


async def test_member_token_is_refused(client, setup):
    resp = await client.delete(_url(setup), headers=auth_headers(setup["member"].id, "member"))
    assert resp.status_code == 403


async def test_unknown_member_is_404(client, db_session, setup):
    stranger = await make_member(db_session)
    await db_session.commit()
    resp = await client.delete(
        f"/api/v1/telegram/communities/{setup['community'].id}/members/{stranger.id}",
        headers=setup["headers"],
    )
    assert resp.status_code == 404
