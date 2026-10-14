"""Telegram infrastructure interface (Protocol).

Business services depend on this interface — never on the concrete
driver or the raw Telegram API.  During testing the TelegramStub
replaces the TelegramDriver without changing any service code (Doc 04 §6, §24).
"""

from __future__ import annotations

from typing import Protocol

from app.infrastructure.telegram.telegram_models import (
    TelegramChat,
    TelegramChatMember,
    TelegramInviteLink,
    TelegramUser,
    TelegramWebhookInfo,
)


class TelegramClient(Protocol):
    """Abstract interface to the Telegram Bot API."""

    # ── Bot management ───────────────────────────────────────────────

    async def get_me(self) -> TelegramUser:
        """Return basic information about the bot."""
        ...

    async def health_check(self) -> bool:
        """Lightweight connectivity / token verification."""
        ...

    # ── Chat operations ──────────────────────────────────────────────

    async def get_chat(self, chat_id: int | str) -> TelegramChat:
        """Retrieve information about a chat by ID."""
        ...

    async def get_chat_member(
        self,
        chat_id: int | str,
        user_id: int,
    ) -> TelegramChatMember:
        """Retrieve a member's status within a chat."""
        ...

    # ── Invite management ────────────────────────────────────────────

    async def create_invite_link(
        self,
        chat_id: int | str,
        *,
        expire_date: int | None = None,
        member_limit: int | None = None,
    ) -> TelegramInviteLink:
        """Create a new invite link for a chat."""
        ...

    # ── Membership management ────────────────────────────────────────

    async def ban_member(
        self,
        chat_id: int | str,
        user_id: int,
    ) -> bool:
        """Ban (kick) a user from a chat."""
        ...

    async def unban_member(
        self,
        chat_id: int | str,
        user_id: int,
    ) -> bool:
        """Unban a previously banned user."""
        ...

    # ── Webhook management ───────────────────────────────────────────

    async def set_webhook(
        self,
        url: str,
        secret_token: str | None = None,
        allowed_updates: list[str] | None = None,
        drop_pending_updates: bool = False,
    ) -> bool:
        """Register a webhook URL with Telegram."""
        ...

    async def delete_webhook(self, drop_pending_updates: bool = False) -> bool:
        """Remove the current webhook."""
        ...

    async def get_webhook_info(self) -> TelegramWebhookInfo:
        """Return the bot's current webhook configuration."""
        ...

    # ── Webhook verification ─────────────────────────────────────────

    def verify_webhook(
        self,
        secret: str,
        header_token: str | None,
    ) -> bool:
        """Verify that an incoming webhook header matches the configured secret."""
        ...
