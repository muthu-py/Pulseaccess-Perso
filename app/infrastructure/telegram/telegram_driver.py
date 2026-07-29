"""Telegram Driver — production implementation of TelegramClient.

Uses httpx.AsyncClient to communicate with the Telegram Bot API.
Contains NO business logic — only HTTP requests, response parsing,
and error translation (Doc 04 §8).
"""

from __future__ import annotations

import httpx

from app.core.config import Settings
from app.core.logging import get_logger
from app.infrastructure.telegram import telegram_constants as tc
from app.infrastructure.telegram.telegram_exceptions import (
    TelegramAuthenticationException,
    TelegramException,
    TelegramNotFoundException,
    TelegramPermissionException,
    TelegramRateLimitException,
    TelegramTimeoutException,
    TelegramUnknownException,
)
from app.infrastructure.telegram.telegram_mapper import TelegramMapper
from app.infrastructure.telegram.telegram_models import (
    TelegramChat,
    TelegramChatMember,
    TelegramInviteLink,
    TelegramUser,
)

logger = get_logger(__name__)


class TelegramDriver:
    """Production Telegram Bot API client using httpx."""

    def __init__(self, settings: Settings) -> None:
        base_url = (
            settings.TELEGRAM_API_BASE_URL.rstrip("/")
            if hasattr(settings, "TELEGRAM_API_BASE_URL")
            else "https://api.telegram.org"
        )
        self._base_url = f"{base_url}/bot{settings.TELEGRAM_BOT_TOKEN}"
        self._webhook_secret = settings.TELEGRAM_WEBHOOK_SECRET

        connect_timeout = getattr(settings, "TELEGRAM_CONNECT_TIMEOUT", 10)
        read_timeout = getattr(settings, "TELEGRAM_READ_TIMEOUT", 30)

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=float(connect_timeout),
                read=float(read_timeout),
                write=float(read_timeout),
                pool=float(read_timeout),
            ),
        )

    # ── Internal helpers ─────────────────────────────────────────────

    async def _request(
        self,
        method: str,
        params: dict | None = None,
    ) -> dict:
        """Send a GET/POST to the Bot API and return the result dict."""
        url = f"{self._base_url}/{method}"
        try:
            response = await self._client.post(url, json=params or {})
        except httpx.TimeoutException as exc:
            logger.error("Telegram timeout on %s", method)
            raise TelegramTimeoutException(str(exc)) from exc
        except httpx.HTTPError as exc:
            logger.error("Telegram HTTP error on %s: %s", method, exc)
            raise TelegramUnknownException(str(exc)) from exc

        self._log_response(method, response.status_code)

        data = response.json()
        if data.get("ok"):
            return data.get("result", {})

        self._raise_for_status(response.status_code, data)
        # unreachable — _raise_for_status always raises
        raise TelegramUnknownException()  # pragma: no cover

    def _log_response(self, method: str, status: int) -> None:
        logger.debug("Telegram %s → HTTP %d", method, status)

    def _raise_for_status(self, status: int, data: dict) -> None:
        description = data.get("description", "Unknown error")
        retry_after = data.get("parameters", {}).get("retry_after", 0)

        if status == 401:
            raise TelegramAuthenticationException(description)
        if status == 403:
            raise TelegramPermissionException(description)
        if status == 404:
            raise TelegramNotFoundException(description)
        if status == 429:
            raise TelegramRateLimitException(description, retry_after=retry_after)
        raise TelegramUnknownException(f"HTTP {status}: {description}")

    # ── Bot management ───────────────────────────────────────────────

    async def get_me(self) -> TelegramUser:
        result = await self._request(tc.GET_ME)
        return TelegramMapper.to_user(result)

    async def health_check(self) -> bool:
        try:
            await self.get_me()
            return True
        except TelegramException:
            return False

    # ── Chat operations ──────────────────────────────────────────────

    async def get_chat(self, chat_id: int | str) -> TelegramChat:
        result = await self._request(tc.GET_CHAT, {"chat_id": chat_id})
        return TelegramMapper.to_chat(result)

    async def get_chat_member(
        self,
        chat_id: int | str,
        user_id: int,
    ) -> TelegramChatMember:
        result = await self._request(
            tc.GET_CHAT_MEMBER,
            {"chat_id": chat_id, "user_id": user_id},
        )
        return TelegramMapper.to_chat_member(result)

    # ── Invite management ────────────────────────────────────────────

    async def create_invite_link(
        self,
        chat_id: int | str,
        *,
        expire_date: int | None = None,
        member_limit: int | None = None,
    ) -> TelegramInviteLink:
        params: dict = {"chat_id": chat_id}
        if expire_date is not None:
            params["expire_date"] = expire_date
        if member_limit is not None:
            params["member_limit"] = member_limit
        result = await self._request(tc.CREATE_CHAT_INVITE_LINK, params)
        return TelegramMapper.to_invite_link(result)

    # ── Membership management ────────────────────────────────────────

    async def ban_member(self, chat_id: int | str, user_id: int) -> bool:
        await self._request(tc.BAN_CHAT_MEMBER, {"chat_id": chat_id, "user_id": user_id})
        return True

    async def unban_member(self, chat_id: int | str, user_id: int) -> bool:
        await self._request(
            tc.UNBAN_CHAT_MEMBER,
            {"chat_id": chat_id, "user_id": user_id, "only_if_banned": True},
        )
        return True

    # ── Webhook management ───────────────────────────────────────────

    async def set_webhook(self, url: str, secret_token: str | None = None) -> bool:
        params: dict = {"url": url}
        if secret_token:
            params["secret_token"] = secret_token
        await self._request(tc.SET_WEBHOOK, params)
        return True

    async def delete_webhook(self) -> bool:
        await self._request(tc.DELETE_WEBHOOK)
        return True

    # ── Webhook verification ─────────────────────────────────────────

    def verify_webhook(self, secret: str, header_token: str | None) -> bool:
        if not header_token:
            return False
        return secret == header_token
