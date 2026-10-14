"""Subscription Expiry Worker — ends access when a plan runs out.

Runs once at startup, then every SUBSCRIPTION_EXPIRY_INTERVAL_HOURS
(default 24). Each cycle:
  1. Marks ACTIVE subscriptions past their end time as EXPIRED.
  2. Handles each expired / cancelled subscription once: queues a
     REMOVE_MEMBER operation unless another of the member's plans in that
     community is still active (Doc 08 §8).

Workers MUST call services, NOT repositories or infrastructure directly.
"""

from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.core.logging import get_logger
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.telegram.telegram_factory import build_telegram_client
from app.modules.subscription.repositories import SubscriptionRepository
from app.modules.subscription.services import SubscriptionService
from app.modules.telegram.repositories import TelegramRepository
from app.modules.telegram.services import TelegramService

logger = get_logger(__name__)


async def run_expiry_cycle(session) -> tuple[int, int]:
    """One pass; returns (subscriptions expired, removals queued)."""
    settings = get_settings()
    subscriptions = SubscriptionService(SubscriptionRepository(session))
    telegram = TelegramService(
        repository=TelegramRepository(session),
        telegram_client=build_telegram_client(settings),
        settings=settings,
    )
    expired = await subscriptions.expire_due()
    queued = await telegram.revoke_ended_access()
    return expired, queued


async def run_subscription_expiry_worker() -> None:
    """Expire due subscriptions and queue group removals."""
    interval_seconds = get_settings().SUBSCRIPTION_EXPIRY_INTERVAL_HOURS * 3600
    logger.debug("Subscription expiry worker started")

    while True:
        try:
            async with SessionLocal() as session:
                expired, queued = await run_expiry_cycle(session)
                await session.commit()
            if expired or queued:
                logger.info(
                    "Expiry cycle: %d subscription(s) expired, %d removal(s) queued",
                    expired, queued,
                )
        except Exception:
            logger.exception("Subscription expiry worker cycle error")

        await asyncio.sleep(interval_seconds)
