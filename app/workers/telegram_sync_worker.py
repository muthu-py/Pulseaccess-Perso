"""Telegram Sync Worker — reconciles PulseAccess state with Telegram.

Re-checks the bot's rights in every linked group (Doc 09 §7): a group where
the bot was removed or demoted moves to NEEDS_ATTENTION, and one where it
was fixed moves back to CONNECTED. Logs only problems; a healthy pass
prints nothing.
"""

from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.core.logging import get_logger
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.telegram.telegram_exceptions import TelegramException
from app.infrastructure.telegram.telegram_factory import build_telegram_client
from app.modules.telegram.repositories import TelegramRepository
from app.modules.telegram.services import TelegramService

logger = get_logger(__name__)


async def run_sync_cycle(session, client) -> None:
    """One pass over the linked communities. The caller commits."""
    settings = get_settings()
    repo = TelegramRepository(session)
    service = TelegramService(
        repository=repo,
        telegram_client=client,
        settings=settings,
    )

    communities = await repo.get_communities_to_verify()
    if not communities:
        return

    try:
        bot = await client.get_me()
    except TelegramException as exc:
        # Telegram or our token is the problem, not the groups; the health worker reports it.
        logger.warning("Sync skipped: getMe failed: %s", exc)
        return

    for community in communities:
        try:
            await service.verify_connection(community, bot.id)
        except Exception:
            logger.exception(
                "Sync worker error for community %s",
                community.id,
            )


async def run_sync_worker() -> None:
    """Periodically reconcile PulseAccess ↔ Telegram membership state."""
    settings = get_settings()

    if not settings.TELEGRAM_SYNC_ENABLED:
        logger.info("Telegram sync worker disabled")
        return

    logger.debug("Telegram sync worker started")

    while True:
        try:
            async with SessionLocal() as session:
                await run_sync_cycle(session, build_telegram_client(settings))
                await session.commit()

        except Exception:
            logger.exception("Sync worker cycle error")

        await asyncio.sleep(300)  # Run every 5 minutes
