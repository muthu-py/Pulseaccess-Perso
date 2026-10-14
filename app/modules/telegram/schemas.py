"""Telegram module Pydantic v2 schemas.

Request/response DTOs for all Telegram API endpoints (Doc 05 §9, Doc 06).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ======================================================================
# Connection Status
# ======================================================================

class TelegramConnectionStatusResponse(BaseModel):
    """Current Telegram connection status for a community."""
    model_config = ConfigDict(from_attributes=True)

    status: str
    telegram_chat_id: str | None = None
    connected_at: datetime | None = None


# ======================================================================
# Invite
# ======================================================================

class InviteResponse(BaseModel):
    """The community's join-request link (no expiry; the bot checks each request)."""
    invite_link: str
    expires_at: datetime | None = None


# ======================================================================
# Webhook (incoming from Telegram)
# ======================================================================

class TelegramWebhookPayload(BaseModel):
    """Minimal Telegram Update envelope — parsed loosely to allow forwarding."""
    model_config = ConfigDict(extra="allow")

    update_id: int
    message: dict | None = None
    my_chat_member: dict | None = None
    chat_member: dict | None = None
    chat_join_request: dict | None = None


# ======================================================================
# Error Response
# ======================================================================

class TelegramErrorResponse(BaseModel):
    """Standard error payload for Telegram-related failures."""
    success: bool = False
    error: dict = Field(default_factory=lambda: {"code": "", "message": ""})
