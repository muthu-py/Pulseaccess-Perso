"""Telegram Retry Worker — processes pending/retrying operations.

Reads queued Telegram operations from the database and delegates
execution to TelegramService.execute_operation (Doc 08 §6).

Workers MUST call services, NOT repositories or infrastructure directly.
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


async def run_retry_worker() -> None:
    """Continuously process pending Telegram operations."""
    settings = get_settings()

    if not settings.TELEGRAM_RETRY_ENABLED:
        logger.info("Telegram retry worker disabled")
        return

    logger.info("Telegram retry worker started")

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

                operations = await repo.find_pending()

                for op in operations:
                    try:
                        await service.execute_operation(op.id)
                    except Exception:
                        logger.exception(
                            "Retry worker failed on operation %s", op.id,
                        )

                await session.commit()

        except Exception:
            logger.exception("Retry worker cycle error")

        await asyncio.sleep(60)  # Run every 1 minute
