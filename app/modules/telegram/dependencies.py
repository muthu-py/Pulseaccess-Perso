"""Telegram module FastAPI dependencies.

Provides dependency injection factories for the Telegram repository,
client, and service.  Follows the existing project pattern from
app/api/dependencies.py (Doc 05 §21).
"""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.infrastructure.database.session import get_db
from app.infrastructure.telegram.telegram_factory import build_telegram_client
from app.infrastructure.telegram.telegram_interface import TelegramClient
from app.modules.telegram.repositories import TelegramRepository
from app.modules.telegram.services import TelegramService


def get_telegram_repository(
    session: AsyncSession = Depends(get_db),
) -> TelegramRepository:
    return TelegramRepository(session=session)


def get_telegram_client(
    settings: Settings = Depends(get_settings),
) -> TelegramClient:
    """Return the real driver when a bot token is set, else the stub."""
    return build_telegram_client(settings)


def get_telegram_service(
    repository: TelegramRepository = Depends(get_telegram_repository),
    client: TelegramClient = Depends(get_telegram_client),
    settings: Settings = Depends(get_settings),
) -> TelegramService:
    return TelegramService(
        repository=repository,
        telegram_client=client,
        settings=settings,
    )
