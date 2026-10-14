"""Telegram infrastructure DTO models.

These represent Telegram Bot API response structures.
Business services consume these typed objects instead of raw JSON (Doc 04 §10-11).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TelegramUser(BaseModel):
    """Represents a Telegram user or bot account."""

    model_config = ConfigDict(extra="ignore")

    id: int
    is_bot: bool = False
    first_name: str = ""
    last_name: str | None = None
    username: str | None = None


class TelegramChat(BaseModel):
    """Represents a Telegram chat (group/supergroup/channel)."""

    model_config = ConfigDict(extra="ignore")

    id: int
    type: str  # "group", "supergroup", "channel", "private"
    title: str | None = None
    username: str | None = None


class TelegramChatMember(BaseModel):
    """Represents a member's status within a chat."""

    model_config = ConfigDict(extra="ignore")

    user: TelegramUser
    status: str  # "creator", "administrator", "member", "restricted", "left", "kicked"


class TelegramInviteLink(BaseModel):
    """Represents a chat invite link created by the bot."""

    model_config = ConfigDict(extra="ignore")

    invite_link: str
    creator: TelegramUser | None = None
    creates_join_request: bool = False
    is_primary: bool = False
    is_revoked: bool = False
    expire_date: int | None = None
    member_limit: int | None = None


class TelegramWebhookInfo(BaseModel):
    """Represents current webhook configuration from getWebhookInfo."""

    model_config = ConfigDict(extra="ignore")

    url: str = ""
    has_custom_certificate: bool = False
    pending_update_count: int = 0
    last_error_date: int | None = None
    last_error_message: str | None = None
    allowed_updates: list[str] = []
