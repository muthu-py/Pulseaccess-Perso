"""Telegram payload mapper.

Converts raw Telegram Bot API JSON payloads into typed internal DTOs (Doc 04 §11).
Business services should never parse raw Telegram JSON directly.
"""

from __future__ import annotations

from typing import Any

from app.infrastructure.telegram.telegram_models import (
    TelegramChat,
    TelegramChatMember,
    TelegramInviteLink,
    TelegramUser,
    TelegramWebhookInfo,
)


class TelegramMapper:
    """Stateless mapper: Telegram JSON → internal DTOs."""

    @staticmethod
    def to_user(data: dict[str, Any]) -> TelegramUser:
        return TelegramUser.model_validate(data)

    @staticmethod
    def to_chat(data: dict[str, Any]) -> TelegramChat:
        return TelegramChat.model_validate(data)

    @staticmethod
    def to_chat_member(data: dict[str, Any]) -> TelegramChatMember:
        return TelegramChatMember.model_validate(data)

    @staticmethod
    def to_invite_link(data: dict[str, Any]) -> TelegramInviteLink:
        return TelegramInviteLink.model_validate(data)

    @staticmethod
    def to_webhook_info(data: dict[str, Any]) -> TelegramWebhookInfo:
        return TelegramWebhookInfo.model_validate(data)
