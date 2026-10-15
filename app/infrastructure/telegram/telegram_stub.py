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
    TelegramWebhookInfo,
)


class TelegramStub:
    """Deterministic stub implementation of TelegramClient."""

    def __init__(self) -> None:
        # Messages "sent" through the stub, kept so tests can inspect them.
        self.sent_messages: list[dict] = []
        self.invite_links: list[dict] = []
        self.approved: list[tuple[str, int]] = []
        self.declined: list[tuple[str, int]] = []
        self.banned: list[tuple[str, int]] = []
        # user_id → status returned by get_chat_member ("member" when absent)
        self.member_status: dict[int, str] = {}

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

    # ── Messaging ────────────────────────────────────────────────────

    async def send_message(
        self,
        chat_id: int | str,
        text: str,
        *,
        reply_markup: dict | None = None,
    ) -> None:
        self.sent_messages.append(
            {"chat_id": chat_id, "text": text, "reply_markup": reply_markup},
        )

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
            status=self.member_status.get(user_id, "member"),
        )

    # ── Invite management ────────────────────────────────────────────

    async def create_invite_link(
        self,
        chat_id: int | str,
        *,
        expire_date: int | None = None,
        member_limit: int | None = None,
        creates_join_request: bool = False,
        name: str | None = None,
    ) -> TelegramInviteLink:
        self.invite_links.append({
            "chat_id": chat_id,
            "expire_date": expire_date,
            "member_limit": member_limit,
            "creates_join_request": creates_join_request,
            "name": name,
        })
        return TelegramInviteLink(
            invite_link=f"https://t.me/+stub_invite_link_{len(self.invite_links)}",
            creates_join_request=creates_join_request,
            expire_date=expire_date,
            member_limit=member_limit,
        )

    # ── Join requests ────────────────────────────────────────────────

    async def approve_join_request(self, chat_id: int | str, user_id: int) -> bool:
        self.approved.append((str(chat_id), user_id))
        return True

    async def decline_join_request(self, chat_id: int | str, user_id: int) -> bool:
        self.declined.append((str(chat_id), user_id))
        return True

    # ── Membership management ────────────────────────────────────────

    async def ban_member(self, chat_id: int | str, user_id: int) -> bool:
        self.banned.append((str(chat_id), user_id))
        return True

    async def unban_member(self, chat_id: int | str, user_id: int) -> bool:
        return True

    # ── Webhook management ───────────────────────────────────────────

    async def set_webhook(
        self,
        url: str,
        secret_token: str | None = None,
        allowed_updates: list[str] | None = None,
        drop_pending_updates: bool = False,
    ) -> bool:
        return True

    async def delete_webhook(self, drop_pending_updates: bool = False) -> bool:
        return True

    async def get_webhook_info(self) -> TelegramWebhookInfo:
        return TelegramWebhookInfo()

    # ── Webhook verification ─────────────────────────────────────────

    def verify_webhook(self, secret: str, header_token: str | None) -> bool:
        if not header_token:
            return False
        return secret == header_token
