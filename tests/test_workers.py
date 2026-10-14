"""Background workers: the operation retry queue and the group sync check.

Telegram is the stub, with a few calls made to fail or report bot rights.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.infrastructure.telegram import telegram_factory
from app.infrastructure.telegram.telegram_exceptions import (
    TelegramPermissionException,
    TelegramRateLimitException,
    TelegramTimeoutException,
    TelegramUnknownException,
)
from app.infrastructure.telegram.telegram_models import TelegramChatMember, TelegramUser
from app.infrastructure.telegram.telegram_stub import TelegramStub
from app.modules.community.models import Community
from app.modules.plan.models import Plan
from app.modules.subscription.enums import SubscriptionStatus
from app.modules.subscription.models import Subscription
from app.modules.telegram import constants as tc
from app.modules.telegram.enums import (
    TelegramConnectionStatus,
    TelegramOperationStatus,
    TelegramOperationType,
)
from app.modules.telegram.models import TelegramOperation
from app.modules.telegram.repositories import TelegramRepository
from app.modules.telegram.services import _parse_backoff
from app.modules.telegram_connect.enums import OwnerType
from app.modules.telegram_connect.models import TelegramAccount
from app.workers.telegram_retry_worker import run_retry_cycle
from app.workers.telegram_sync_worker import run_sync_cycle
from tests.helpers import make_community, make_member

CREATOR_TG_ID = 4242


class FlakyStub(TelegramStub):
    """Stub whose ban / getChatMember can fail or report the bot's admin rights."""

    def __init__(self) -> None:
        super().__init__()
        self.ban_error: Exception | None = None
        self.member_error: Exception | None = None
        self.bot_rights = True

    async def ban_member(self, chat_id, user_id):
        if self.ban_error is not None:
            raise self.ban_error
        return await super().ban_member(chat_id, user_id)

    async def get_chat_member(self, chat_id, user_id):
        if self.member_error is not None:
            raise self.member_error
        if self.bot_rights:
            return TelegramChatMember(
                user=TelegramUser(id=user_id, first_name="Bot", is_bot=True),
                status="administrator",
                can_invite_users=True,
                can_restrict_members=True,
            )
        return TelegramChatMember(
            user=TelegramUser(id=user_id, first_name="Bot", is_bot=True), status="member",
        )


@pytest.fixture
def stub() -> FlakyStub:
    return FlakyStub()


@pytest.fixture
async def setup(db_session: AsyncSession):
    """A connected community whose creator has Telegram, and a member."""
    creator_id = uuid.uuid4()
    community = await make_community(db_session, creator_id)
    community.telegram_join_link = "https://t.me/+old"
    db_session.add(TelegramAccount(
        owner_type=OwnerType.CREATOR.value,
        owner_id=creator_id,
        telegram_user_id=str(CREATOR_TG_ID),
        phone="+919800000000",
    ))
    plan = Plan(community_id=community.id, name="Monthly", price_paise=49900, duration_days=30)
    db_session.add(plan)
    member = await make_member(db_session)
    await db_session.flush()
    return {"community": community, "plan": plan, "member": member}


async def _queue_removal(db: AsyncSession, setup, **values) -> TelegramOperation:
    op = TelegramOperation(
        operation_type=TelegramOperationType.REMOVE_MEMBER.value,
        community_id=setup["community"].id,
        member_id=setup["member"].id,
        **{"status": TelegramOperationStatus.PENDING.value, **values},
    )
    db.add(op)
    await db.commit()
    return op


async def _reload(db: AsyncSession, op: TelegramOperation) -> TelegramOperation:
    await db.refresh(op)
    return op


def _creator_dms(stub: TelegramStub) -> list[str]:
    return [m["text"] for m in stub.sent_messages if str(m["chat_id"]) == str(CREATOR_TG_ID)]


async def _status(db: AsyncSession, community: Community) -> str:
    await db.refresh(community)
    return community.telegram_connection_status


# ── retry queue ─────────────────────────────────────────────────────────


async def test_removal_runs_ban(db_session, setup, stub):
    op = await _queue_removal(db_session, setup)
    await run_retry_cycle(db_session, stub)
    assert (await _reload(db_session, op)).status == TelegramOperationStatus.COMPLETED.value
    assert len(stub.banned) == 1


async def test_removal_skipped_when_plan_renewed(db_session, setup, stub):
    op = await _queue_removal(db_session, setup)
    now = datetime.now(timezone.utc)
    db_session.add(Subscription(
        member_id=setup["member"].id,
        plan_id=setup["plan"].id,
        status=SubscriptionStatus.ACTIVE.value,
        starts_at=now,
        ends_at=now + timedelta(days=30),
    ))
    await db_session.commit()

    await run_retry_cycle(db_session, stub)

    assert (await _reload(db_session, op)).status == TelegramOperationStatus.COMPLETED.value
    assert stub.banned == []


async def test_unexpected_error_is_retried_then_fails(db_session, setup, stub):
    stub.ban_error = RuntimeError("boom")
    op = await _queue_removal(db_session, setup)

    await run_retry_cycle(db_session, stub)
    op = await _reload(db_session, op)
    assert op.status == TelegramOperationStatus.RETRYING.value
    assert op.retry_count == 1
    assert "boom" in op.last_error

    op.retry_count = get_settings().TELEGRAM_MAX_RETRIES
    op.scheduled_at = None
    await db_session.commit()
    await run_retry_cycle(db_session, stub)
    assert (await _reload(db_session, op)).status == TelegramOperationStatus.FAILED.value


async def test_stuck_processing_op_is_picked_up_after_its_lease(db_session, setup, stub):
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    future = datetime.now(timezone.utc) + timedelta(minutes=5)
    expired = await _queue_removal(
        db_session, setup, status=TelegramOperationStatus.PROCESSING.value, scheduled_at=past,
    )
    running = await _queue_removal(
        db_session, setup, status=TelegramOperationStatus.PROCESSING.value, scheduled_at=future,
    )

    await run_retry_cycle(db_session, stub)

    assert (await _reload(db_session, expired)).status == TelegramOperationStatus.COMPLETED.value
    assert (await _reload(db_session, running)).status == TelegramOperationStatus.PROCESSING.value


async def test_retry_uses_configured_backoff(db_session, setup, stub):
    stub.ban_error = TelegramTimeoutException()
    op = await _queue_removal(db_session, setup)
    await run_retry_cycle(db_session, stub)
    op = await _reload(db_session, op)
    delay = op.scheduled_at.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)
    # First step of TELEGRAM_RETRY_BACKOFF ("1m,...").
    assert timedelta(seconds=50) < delay <= timedelta(minutes=1)


async def test_retry_waits_at_least_retry_after(db_session, setup, stub):
    stub.ban_error = TelegramRateLimitException("Too Many Requests", retry_after=600)
    op = await _queue_removal(db_session, setup)
    await run_retry_cycle(db_session, stub)
    op = await _reload(db_session, op)
    delay = op.scheduled_at.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)
    assert timedelta(minutes=9) < delay <= timedelta(minutes=10)


def test_parse_backoff():
    assert _parse_backoff("30s, 2m,1h") == [
        timedelta(seconds=30), timedelta(minutes=2), timedelta(hours=1),
    ]
    assert _parse_backoff("nonsense")[0] == timedelta(minutes=1)


# ── sync check ──────────────────────────────────────────────────────────


async def test_sync_healthy_group_changes_nothing(db_session, setup, stub):
    await run_sync_cycle(db_session, stub)
    assert await _status(db_session, setup["community"]) == TelegramConnectionStatus.CONNECTED.value
    assert _creator_dms(stub) == []


async def test_sync_bot_demoted_needs_attention(db_session, setup, stub):
    stub.bot_rights = False
    await run_sync_cycle(db_session, stub)
    community = setup["community"]
    assert await _status(db_session, community) == TelegramConnectionStatus.NEEDS_ATTENTION.value
    assert community.telegram_join_link is None
    assert _creator_dms(stub) == [tc.MSG_GROUP_ACCESS_LOST.format(community=community.name)]

    # Another pass does not message the creator again.
    await run_sync_cycle(db_session, stub)
    assert len(_creator_dms(stub)) == 1


@pytest.mark.parametrize("error", [
    TelegramPermissionException("Forbidden: bot was kicked from the supergroup chat"),
    TelegramUnknownException("HTTP 400: Bad Request: chat not found"),
])
async def test_sync_bot_removed_needs_attention(db_session, setup, stub, error):
    stub.member_error = error
    await run_sync_cycle(db_session, stub)
    assert (
        await _status(db_session, setup["community"])
        == TelegramConnectionStatus.NEEDS_ATTENTION.value
    )


@pytest.mark.parametrize("error", [
    TelegramTimeoutException(),
    TelegramRateLimitException(retry_after=5),
    TelegramUnknownException("HTTP 502: Bad Gateway"),
])
async def test_sync_temporary_error_changes_nothing(db_session, setup, stub, error):
    stub.member_error = error
    await run_sync_cycle(db_session, stub)
    assert await _status(db_session, setup["community"]) == TelegramConnectionStatus.CONNECTED.value
    assert _creator_dms(stub) == []


async def test_sync_recovers_when_bot_is_admin_again(db_session, setup, stub):
    community = setup["community"]
    await TelegramRepository(db_session).update_connection_status(
        community.id, TelegramConnectionStatus.NEEDS_ATTENTION,
    )
    await db_session.commit()

    await run_sync_cycle(db_session, stub)

    assert await _status(db_session, community) == TelegramConnectionStatus.CONNECTED.value
    assert _creator_dms(stub) == [tc.MSG_GROUP_ACCESS_RESTORED.format(community=community.name)]


async def test_sync_skips_when_get_me_fails(db_session, setup, stub):
    async def broken_get_me():
        raise TelegramTimeoutException()

    stub.get_me = broken_get_me
    stub.bot_rights = False
    await run_sync_cycle(db_session, stub)
    assert await _status(db_session, setup["community"]) == TelegramConnectionStatus.CONNECTED.value


# ── shared client ───────────────────────────────────────────────────────


async def test_factory_reuses_one_driver_and_closes_it():
    settings = get_settings().model_copy(
        update={"TELEGRAM_BOT_TOKEN": "1:TEST", "TELEGRAM_USE_STUB": False},
    )
    first = telegram_factory.build_telegram_client(settings)
    assert telegram_factory.build_telegram_client(settings) is first

    await telegram_factory.close_telegram_clients()
    assert first._client.is_closed
    assert telegram_factory.build_telegram_client(settings) is not first
    await telegram_factory.close_telegram_clients()
