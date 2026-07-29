"""Subscription Expiry Worker — queues member removal on subscription expiration.

Detects subscriptions that have expired (status EXPIRED or CANCELLED)
where the member still has Telegram access, and queues a REMOVE_MEMBER
operation for asynchronous execution (Doc 08 §8).

Workers MUST call services, NOT repositories or infrastructure directly.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import get_logger
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.telegram.telegram_driver import TelegramDriver
from app.infrastructure.telegram.telegram_stub import TelegramStub
from app.modules.member.models import Member
from app.modules.subscription.models import Subscription
from app.modules.telegram.enums import TelegramConnectionStatus
from app.modules.telegram.repositories import TelegramRepository
from app.modules.telegram.services import TelegramService

logger = get_logger(__name__)

# Subscription statuses that indicate expiry / cancellation
EXPIRED_STATUSES = {"expired", "cancelled", "EXPIRED", "CANCELLED"}


async def run_subscription_expiry_worker() -> None:
    """Queue Telegram member removals for expired subscriptions."""
    settings = get_settings()
    logger.info("Subscription expiry worker started")

    while True:
        try:
            async with SessionLocal() as session:
                repo = TelegramRepository(session)

                if settings.is_development:
                    client = TelegramStub()
                else:
                    client = TelegramDriver(settings=settings)

                service = TelegramService(
                    repository=repo,
                    telegram_client=client,
                    settings=settings,
                )

                # Find subscriptions with expired/cancelled status
                stmt = (
                    select(Subscription)
                    .where(Subscription.status.in_(EXPIRED_STATUSES))
                )
                result = await session.execute(stmt)
                expired_subs = result.scalars().all()

                for sub in expired_subs:
                    try:
                        # Get the member
                        member = await repo.get_member_by_id(sub.member_id)
                        if member is None or not member.telegram_user_id:
                            # No Telegram account linked — nothing to revoke
                            continue

                        # Get the community from member's community_id
                        community = await repo.get_community_by_id(member.community_id)
                        if community is None:
                            continue

                        # Only act on CONNECTED communities
                        if community.telegram_connection_status != TelegramConnectionStatus.CONNECTED.value:
                            continue

                        # Queue the removal via service (not directly via repo)
                        await service.revoke_access(
                            community_id=community.id,
                            member_id=member.id,
                        )
                        logger.info(
                            "Queued REMOVE_MEMBER for expired member %s in community %s",
                            member.id,
                            community.id,
                        )

                    except Exception:
                        logger.exception(
                            "Expiry worker error for subscription %s", sub.id,
                        )

                await session.commit()

        except Exception:
            logger.exception("Subscription expiry worker cycle error")

        await asyncio.sleep(300)  # Run every 5 minutes
