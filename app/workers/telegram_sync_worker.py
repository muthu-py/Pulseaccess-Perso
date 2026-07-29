"""Telegram Sync Worker — reconciles PulseAccess state with Telegram.

Compares PulseAccess membership records against Telegram group
membership and queues corrective operations for inconsistencies (Doc 09 §7).
"""

from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.core.logging import get_logger
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.telegram.telegram_driver import TelegramDriver
from app.infrastructure.telegram.telegram_stub import TelegramStub
from app.modules.telegram.enums import TelegramConnectionStatus
from app.modules.telegram.repositories import TelegramRepository
from app.modules.telegram.services import TelegramService

logger = get_logger(__name__)


async def run_sync_worker() -> None:
    """Periodically reconcile PulseAccess ↔ Telegram membership state."""
    settings = get_settings()

    if not settings.TELEGRAM_SYNC_ENABLED:
        logger.info("Telegram sync worker disabled")
        return

    logger.info("Telegram sync worker started")

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

                communities = await repo.get_connected_communities()

                for community in communities:
                    try:
                        # Verify the bot is still in the group
                        bot = await client.get_me()
                        member = await client.get_chat_member(
                            community.telegram_chat_id,
                            bot.id,
                        )
                        if member.status in ("left", "kicked"):
                            await repo.update_connection_status(
                                community.id,
                                TelegramConnectionStatus.NEEDS_ATTENTION,
                            )
                            logger.warning(
                                "Sync: community %s → NEEDS_ATTENTION (bot removed)",
                                community.id,
                            )
                    except Exception:
                        logger.exception(
                            "Sync worker error for community %s",
                            community.id,
                        )

                await session.commit()

        except Exception:
            logger.exception("Sync worker cycle error")

        await asyncio.sleep(300)  # Run every 5 minutes
