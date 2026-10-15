"""Telegram connect routers — "Connect Telegram" for creators and members."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_creator, get_current_member
from app.modules.auth.schemas import BaseSuccessResponse
from app.modules.telegram_connect.dependencies import get_telegram_connect_service
from app.modules.telegram_connect.enums import OwnerType
from app.modules.telegram_connect.schemas import (
    ConnectTelegramResponse,
    TelegramConnectionResponse,
)
from app.modules.telegram_connect.services import TelegramConnectService

router = APIRouter(prefix="/api/v1/telegram/connect", tags=["telegram-connect"])


@router.post(
    "/creator",
    response_model=BaseSuccessResponse[ConnectTelegramResponse],
    summary="Connect Telegram (creator)",
    description="Returns a one-time link that opens the bot to connect this creator's Telegram.",
)
async def connect_creator(
    creator_id: uuid.UUID = Depends(get_current_creator),
    service: TelegramConnectService = Depends(get_telegram_connect_service),
) -> BaseSuccessResponse[ConnectTelegramResponse]:
    return BaseSuccessResponse(data=await service.start_connect(OwnerType.CREATOR, creator_id))


@router.get(
    "/creator",
    response_model=BaseSuccessResponse[TelegramConnectionResponse],
    summary="Telegram connection status (creator)",
)
async def creator_connection(
    creator_id: uuid.UUID = Depends(get_current_creator),
    service: TelegramConnectService = Depends(get_telegram_connect_service),
) -> BaseSuccessResponse[TelegramConnectionResponse]:
    return BaseSuccessResponse(data=await service.get_connection(OwnerType.CREATOR, creator_id))


@router.post(
    "/member",
    response_model=BaseSuccessResponse[ConnectTelegramResponse],
    summary="Connect Telegram (member)",
    description="Returns a one-time link that opens the bot to connect this member's Telegram.",
)
async def connect_member(
    member_id: uuid.UUID = Depends(get_current_member),
    service: TelegramConnectService = Depends(get_telegram_connect_service),
) -> BaseSuccessResponse[ConnectTelegramResponse]:
    return BaseSuccessResponse(data=await service.start_connect(OwnerType.MEMBER, member_id))


@router.get(
    "/member",
    response_model=BaseSuccessResponse[TelegramConnectionResponse],
    summary="Telegram connection status (member)",
)
async def member_connection(
    member_id: uuid.UUID = Depends(get_current_member),
    service: TelegramConnectService = Depends(get_telegram_connect_service),
) -> BaseSuccessResponse[TelegramConnectionResponse]:
    return BaseSuccessResponse(data=await service.get_connection(OwnerType.MEMBER, member_id))
