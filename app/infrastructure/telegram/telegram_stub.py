"""Telegram Stub — test/development replacement for TelegramDriver.

Returns deterministic responses.  Never contacts Telegram (Doc 04 §9).
Implements the same TelegramClient Protocol so services need no changes.
"""

from __future__ import annotations

from app.infrastructure.telegram.telegram_models import (
    TelegramChat,
    TelegramChatMember,
    TelegramInviteLink,
    TelegramUser,
)


class TelegramStub:
    """Deterministic stub implementation of TelegramClient."""

    # ── Bot management ───────────────────────────────────────────────

    async def get_me(self) -> TelegramUser:
        return TelegramUser(
            id=9999999999,
            is_bot=True,
            first_name="PulseAccessBot",
            username="pulse_access_test_bot",
        )

    async def health_check(self) -> bool:
        return True

    # ── Chat operations ──────────────────────────────────────────────

    async def get_chat(self, chat_id: int | str) -> TelegramChat:
        return TelegramChat(
            id=int(chat_id) if isinstance(chat_id, (int, str)) else -1001234567890,
            type="supergroup",
            title="Stub Community Group",
        )

    async def get_chat_member(
        self,
        chat_id: int | str,
        user_id: int,
    ) -> TelegramChatMember:
        return TelegramChatMember(
            user=TelegramUser(id=user_id, first_name="StubUser"),
            status="member",
        )

    # ── Invite management ────────────────────────────────────────────

    async def create_invite_link(
        self,
        chat_id: int | str,
        *,
        expire_date: int | None = None,
        member_limit: int | None = None,
    ) -> TelegramInviteLink:
        return TelegramInviteLink(
            invite_link="https://t.me/joinchat/stub_invite_link",
            expire_date=expire_date,
            member_limit=member_limit,
        )

    # ── Membership management ────────────────────────────────────────

    async def ban_member(self, chat_id: int | str, user_id: int) -> bool:
        return True

    async def unban_member(self, chat_id: int | str, user_id: int) -> bool:
        return True

    # ── Webhook management ───────────────────────────────────────────

    async def set_webhook(self, url: str, secret_token: str | None = None) -> bool:
        return True

    async def delete_webhook(self) -> bool:
        return True

    # ── Webhook verification ─────────────────────────────────────────

    def verify_webhook(self, secret: str, header_token: str | None) -> bool:
        if not header_token:
            return False
        return secret == header_token
