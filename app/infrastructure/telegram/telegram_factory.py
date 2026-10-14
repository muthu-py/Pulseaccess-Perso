"""Builds the Telegram client used by the API and the background workers."""

from __future__ import annotations

from app.core.config import Settings
from app.infrastructure.telegram.telegram_driver import TelegramDriver
from app.infrastructure.telegram.telegram_interface import TelegramClient
from app.infrastructure.telegram.telegram_stub import TelegramStub

# One driver (and so one HTTP connection pool) per token for the whole process.
_drivers: dict[tuple[str, str], TelegramDriver] = {}


def build_telegram_client(settings: Settings) -> TelegramClient:
    """Return the real driver when a bot token is configured, else the stub.

    TELEGRAM_USE_STUB=true forces the stub even when a token is set.

    Keying this on the token (not APP_ENV) means a developer running locally
    with a real bot token talks to Telegram, while tests and setups without
    a token never make network calls.

    The driver is shared: requests and workers reuse one connection pool
    instead of each opening one that is never closed.
    """
    if settings.TELEGRAM_USE_STUB or not settings.TELEGRAM_BOT_TOKEN:
        return TelegramStub()
    key = (settings.TELEGRAM_BOT_TOKEN, settings.TELEGRAM_API_BASE_URL)
    driver = _drivers.get(key)
    if driver is None:
        driver = TelegramDriver(settings=settings)
        _drivers[key] = driver
    return driver


async def close_telegram_clients() -> None:
    """Close the shared drivers' connection pools (called on app shutdown)."""
    drivers = list(_drivers.values())
    _drivers.clear()
    for driver in drivers:
        await driver.aclose()
