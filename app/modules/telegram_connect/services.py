"""Telegram connect service — links a creator or member login to Telegram.

Flow (same for both account types):
  1. The logged-in user asks for a link → one-time token → t.me/<bot>?start=<token>
  2. They tap Start → the bot remembers which Telegram user opened the token
     and asks them to share their phone number.
  3. They share their contact → the phone must be their own and must match
     the phone on their PulseAccess account → the Telegram account is saved.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.phone import normalize_phone
from app.infrastructure.telegram.telegram_exceptions import TelegramException
from app.infrastructure.telegram.telegram_interface import TelegramClient
from app.modules.telegram_connect import constants as cc
from app.modules.telegram_connect.enums import OwnerType
from app.modules.telegram_connect.exceptions import (
    PhoneRequiredError,
    TelegramAlreadyConnectedError,
    TelegramNotConnectedError,
)
from app.modules.telegram_connect.models import TelegramLinkToken
from app.modules.telegram_connect.repositories import TelegramConnectRepository
from app.modules.telegram_connect.schemas import (
    ConnectTelegramResponse,
    TelegramConnectionResponse,
)

logger = get_logger(__name__)

_SHARE_PHONE_KEYBOARD = {
    "keyboard": [[{"text": cc.SHARE_PHONE_BUTTON, "request_contact": True}]],
    "resize_keyboard": True,
    "one_time_keyboard": True,
}
_REMOVE_KEYBOARD = {"remove_keyboard": True}


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _ensure_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class TelegramConnectService:
    """Business logic for connecting accounts to Telegram."""

    def __init__(
        self,
        repository: TelegramConnectRepository,
        telegram_client: TelegramClient,
        settings: Settings,
    ) -> None:
        self._repo = repository
        self._telegram = telegram_client
        self._settings = settings

    # ══════════════════════════════════════════════════════════════════
    #  Site side
    # ══════════════════════════════════════════════════════════════════

    async def start_connect(
        self,
        owner_type: OwnerType,
        owner_id: uuid.UUID,
    ) -> ConnectTelegramResponse:
        """Create a one-time bot link for this account."""
        if not await self._repo.get_owner_phone(owner_type, owner_id):
            raise PhoneRequiredError()

        if await self._repo.get_account(owner_type, owner_id) is not None:
            raise TelegramAlreadyConnectedError()

        await self._repo.invalidate_tokens(owner_type, owner_id)

        raw_token = secrets.token_urlsafe(cc.LINK_TOKEN_BYTES)
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=cc.LINK_TOKEN_EXPIRY_MINUTES,
        )
        await self._repo.create_token(_hash_token(raw_token), owner_type, owner_id, expires_at)

        bot_username = self._settings.TELEGRAM_BOT_USERNAME.lstrip("@")
        logger.info("Telegram connect link created for %s %s", owner_type.value, owner_id)

        return ConnectTelegramResponse(
            telegram_link=f"https://t.me/{bot_username}?start={raw_token}",
            expires_at=expires_at,
        )

    async def get_connection(
        self,
        owner_type: OwnerType,
        owner_id: uuid.UUID,
    ) -> TelegramConnectionResponse:
        account = await self._repo.get_account(owner_type, owner_id)
        if account is None:
            return TelegramConnectionResponse(connected=False)
        return TelegramConnectionResponse(
            connected=True,
            telegram_username=account.telegram_username,
            linked_at=account.linked_at,
        )

    async def is_connected(self, owner_type: OwnerType, owner_id: uuid.UUID) -> bool:
        return await self._repo.get_account(owner_type, owner_id) is not None

    async def ensure_connected(self, owner_type: OwnerType, owner_id: uuid.UUID) -> None:
        """Raise unless this account has connected Telegram."""
        if not await self.is_connected(owner_type, owner_id):
            raise TelegramNotConnectedError()

    # ══════════════════════════════════════════════════════════════════
    #  Bot side (webhook)
    # ══════════════════════════════════════════════════════════════════

    async def handle_private_message(self, message: dict) -> None:
        """Handle a message sent to the bot in a private chat."""
        chat = message.get("chat", {})
        if chat.get("type") != "private":
            return  # group chatter is not ours to answer

        chat_id = chat.get("id")
        from_user = message.get("from", {})
        telegram_user_id = str(from_user.get("id", ""))
        if not chat_id or not telegram_user_id:
            return

        if "contact" in message:
            await self._handle_contact(chat_id, from_user, message["contact"])
            return

        text = (message.get("text") or "").strip()
        if text.startswith("/start"):
            parts = text.split(maxsplit=1)
            if len(parts) == 2:
                await self._handle_start_token(chat_id, telegram_user_id, parts[1])
                return

        # Plain /start, /help or any other text: nudge them along.
        if await self._repo.get_pending_token_for_telegram_user(telegram_user_id):
            await self._reply(chat_id, cc.MSG_SHARE_PHONE, _SHARE_PHONE_KEYBOARD)
        else:
            await self._reply(chat_id, cc.MSG_OPEN_FROM_SITE)

    async def _handle_start_token(
        self,
        chat_id: int,
        telegram_user_id: str,
        raw_token: str,
    ) -> None:
        token = await self._repo.get_token_by_hash(_hash_token(raw_token))
        if not self._token_usable(token, telegram_user_id):
            await self._reply(chat_id, cc.MSG_LINK_EXPIRED, _REMOVE_KEYBOARD)
            return

        await self._repo.claim_token(token.id, telegram_user_id)
        await self._reply(chat_id, cc.MSG_SHARE_PHONE, _SHARE_PHONE_KEYBOARD)

    async def _handle_contact(self, chat_id: int, from_user: dict, contact: dict) -> None:
        telegram_user_id = str(from_user.get("id"))

        # A forwarded contact card carries someone else's user_id (or none).
        if str(contact.get("user_id")) != telegram_user_id:
            await self._reply(chat_id, cc.MSG_NOT_OWN_CONTACT, _SHARE_PHONE_KEYBOARD)
            return

        token = await self._repo.get_pending_token_for_telegram_user(telegram_user_id)
        if token is None:
            await self._reply(chat_id, cc.MSG_LINK_EXPIRED, _REMOVE_KEYBOARD)
            return

        owner_type = OwnerType(token.owner_type)
        owner_phone = await self._repo.get_owner_phone(owner_type, token.owner_id)
        shared_phone = normalize_phone(contact.get("phone_number", ""))
        if not owner_phone or normalize_phone(owner_phone) != shared_phone:
            logger.info(
                "Telegram connect phone mismatch for %s %s",
                owner_type.value,
                token.owner_id,
            )
            await self._reply(chat_id, cc.MSG_PHONE_MISMATCH, _REMOVE_KEYBOARD)
            return

        taken = await self._repo.get_account_by_telegram_id(owner_type, telegram_user_id)
        if taken is not None and taken.owner_id != token.owner_id:
            await self._reply(chat_id, cc.MSG_ALREADY_USED, _REMOVE_KEYBOARD)
            return

        if await self._repo.get_account(owner_type, token.owner_id) is None:
            await self._repo.create_account(
                owner_type=owner_type,
                owner_id=token.owner_id,
                telegram_user_id=telegram_user_id,
                telegram_username=from_user.get("username"),
                phone=shared_phone,
            )
        await self._repo.mark_token_used(token.id)

        logger.info("Telegram connected for %s %s", owner_type.value, token.owner_id)
        await self._reply(chat_id, cc.MSG_CONNECTED, _REMOVE_KEYBOARD)

    @staticmethod
    def _token_usable(token: TelegramLinkToken | None, telegram_user_id: str) -> bool:
        if token is None or token.used_at is not None:
            return False
        if _ensure_utc(token.expires_at) <= datetime.now(timezone.utc):
            return False
        # Once one Telegram user has opened a link, nobody else can use it.
        return token.telegram_user_id in (None, telegram_user_id)

    async def _reply(self, chat_id: int, text: str, reply_markup: dict | None = None) -> None:
        try:
            await self._telegram.send_message(chat_id, text, reply_markup=reply_markup)
        except TelegramException:
            # The DB changes stand; the user can tap Start again for a reply.
            logger.exception("Failed to send Telegram reply to chat %s", chat_id)
