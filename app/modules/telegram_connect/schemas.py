"""Telegram connect request/response schemas."""

from datetime import datetime

from pydantic import BaseModel


class ConnectTelegramResponse(BaseModel):
    """Link that opens the bot with this account's one-time code."""

    telegram_link: str
    expires_at: datetime


class TelegramConnectionResponse(BaseModel):
    """Whether this account has a connected Telegram account."""

    connected: bool
    telegram_username: str | None = None
    linked_at: datetime | None = None
