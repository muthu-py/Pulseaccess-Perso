"""Telegram connect FastAPI dependencies, including the "must be connected" guards."""

from __future__ import annotations

import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_creator, get_current_member
from app.core.config import Settings, get_settings
from app.infrastructure.database.session import get_db
from app.infrastructure.telegram.telegram_factory import build_telegram_client
from app.infrastructure.telegram.telegram_interface import TelegramClient
from app.modules.telegram_connect.enums import OwnerType
from app.modules.telegram_connect.repositories import TelegramConnectRepository
from app.modules.telegram_connect.services import TelegramConnectService


def get_telegram_client(
    settings: Settings = Depends(get_settings),
) -> TelegramClient:
    return build_telegram_client(settings)


def get_telegram_connect_service(
    session: AsyncSession = Depends(get_db),
    client: TelegramClient = Depends(get_telegram_client),
    settings: Settings = Depends(get_settings),
) -> TelegramConnectService:
    return TelegramConnectService(
        repository=TelegramConnectRepository(session=session),
        telegram_client=client,
        settings=settings,
    )


async def require_creator_telegram(
    creator_id: uuid.UUID = Depends(get_current_creator),
    service: TelegramConnectService = Depends(get_telegram_connect_service),
) -> uuid.UUID:
    """Authenticated creator who has connected Telegram. Returns creator_id."""
    await service.ensure_connected(OwnerType.CREATOR, creator_id)
    return creator_id


async def require_member_telegram(
    member_id: uuid.UUID = Depends(get_current_member),
    service: TelegramConnectService = Depends(get_telegram_connect_service),
) -> uuid.UUID:
    """Authenticated member who has connected Telegram. Returns member_id."""
    await service.ensure_connected(OwnerType.MEMBER, member_id)
    return member_id
