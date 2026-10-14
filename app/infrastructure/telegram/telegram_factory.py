"""Builds the Telegram client used by the API and the background workers."""

from __future__ import annotations

from app.core.config import Settings
from app.infrastructure.telegram.telegram_driver import TelegramDriver
from app.infrastructure.telegram.telegram_interface import TelegramClient
from app.infrastructure.telegram.telegram_stub import TelegramStub


def build_telegram_client(settings: Settings) -> TelegramClient:
    """Return the real driver when a bot token is configured, else the stub.

    Keying this on the token (not APP_ENV) means a developer running locally
    with a real bot token talks to Telegram, while tests and setups without
    a token never make network calls.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        return TelegramStub()
    return TelegramDriver(settings=settings)
