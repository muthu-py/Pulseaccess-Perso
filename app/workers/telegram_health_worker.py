"""Telegram Health Worker — monitors bot connectivity.

Periodically calls TelegramService.health_check(). Logs only when the
Telegram Bot API is unavailable; a healthy check prints nothing (Doc 08 §9).

Workers MUST call services, NOT infrastructure or repositories directly.
"""

from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.core.logging import get_logger
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.telegram.telegram_factory import build_telegram_client
from app.modules.telegram.repositories import TelegramRepository
from app.modules.telegram.services import TelegramService

logger = get_logger(__name__)


async def run_health_worker() -> None:
    """Periodically verify Telegram Bot API availability."""
    settings = get_settings()

    if not settings.TELEGRAM_HEALTH_ENABLED:
        logger.info("Telegram health worker disabled")
        return

    logger.debug("Telegram health worker started")

    while True:
        try:
            async with SessionLocal() as session:
                repo = TelegramRepository(session)

                client = build_telegram_client(settings)

                service = TelegramService(
                    repository=repo,
                    telegram_client=client,
                    settings=settings,
                )

                healthy = await service.health_check()

                if not healthy:
                    logger.warning("Telegram health check: FAILED — bot API unavailable")

        except Exception:
            logger.exception("Health worker error")

        await asyncio.sleep(120)  # Check every 2 minutes
