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


async def run_retry_cycle(session, client) -> None:
    """Run every due operation, committing each one on its own."""
    settings = get_settings()
    repo = TelegramRepository(session)
    service = TelegramService(
        repository=repo,
        telegram_client=client,
        settings=settings,
    )

    operation_ids = [op.id for op in await repo.find_pending()]

    for operation_id in operation_ids:
        try:
            await service.execute_operation(operation_id)
            await session.commit()
        except Exception:
            # Leaves the op as it was; it is retried on a later pass.
            await session.rollback()
            logger.exception(
                "Retry worker failed on operation %s", operation_id,
            )


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
                await run_retry_cycle(session, build_telegram_client(settings))

        except Exception:
            logger.exception("Retry worker cycle error")

        await asyncio.sleep(60)  # Run every 1 minute
