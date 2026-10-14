"""Register, inspect, or remove the Telegram bot webhook.

One webhook per bot: Telegram sends every update for the bot to
<base_url>/api/v1/webhooks/telegram. For local development, expose the
API with ngrok and pass its https URL as the base.

Usage:
    python -m scripts.telegram_webhook set https://<id>.ngrok-free.app
    python -m scripts.telegram_webhook set            # uses TELEGRAM_WEBHOOK_BASE_URL
    python -m scripts.telegram_webhook info
    python -m scripts.telegram_webhook delete
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from app.core.config import get_settings
from app.infrastructure.telegram.telegram_driver import TelegramDriver
from app.modules.telegram import constants as tc


def _build_webhook_url(base_url: str) -> str:
    base = base_url.strip().rstrip("/")
    if not base.startswith("https://"):
        raise SystemExit("Telegram requires an https webhook URL (got %r)." % base)
    return f"{base}{tc.WEBHOOK_PATH}"


async def _set(driver: TelegramDriver, base_url: str, secret: str, drop_pending: bool) -> None:
    if not secret:
        raise SystemExit("TELEGRAM_WEBHOOK_SECRET is empty; set it in .env first.")
    url = _build_webhook_url(base_url)
    await driver.set_webhook(
        url,
        secret_token=secret,
        allowed_updates=tc.WEBHOOK_ALLOWED_UPDATES,
        drop_pending_updates=drop_pending,
    )
    print(f"Webhook set → {url}")
    await _info(driver)


async def _info(driver: TelegramDriver) -> None:
    info = await driver.get_webhook_info()
    print(f"url:              {info.url or '(none)'}")
    print(f"allowed_updates:  {info.allowed_updates or '(all default)'}")
    print(f"pending updates:  {info.pending_update_count}")
    if info.last_error_message:
        print(f"last error:       {info.last_error_message}")


async def _main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    set_cmd = sub.add_parser("set", help="Register the webhook URL")
    set_cmd.add_argument("base_url", nargs="?", help="Public https base URL (e.g. ngrok)")
    set_cmd.add_argument(
        "--drop-pending",
        action="store_true",
        help="Discard updates Telegram queued while no webhook was reachable",
    )
    sub.add_parser("info", help="Show the current webhook configuration")
    sub.add_parser("delete", help="Remove the webhook")

    args = parser.parse_args(argv)
    settings = get_settings()
    if not settings.TELEGRAM_BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN is empty; set it in .env first.")

    driver = TelegramDriver(settings=settings)
    if args.command == "set":
        base_url = args.base_url or settings.TELEGRAM_WEBHOOK_BASE_URL
        if not base_url:
            raise SystemExit("Pass a base URL or set TELEGRAM_WEBHOOK_BASE_URL.")
        await _set(driver, base_url, settings.TELEGRAM_WEBHOOK_SECRET, args.drop_pending)
    elif args.command == "info":
        await _info(driver)
    else:
        await driver.delete_webhook()
        print("Webhook deleted.")


if __name__ == "__main__":
    asyncio.run(_main(sys.argv[1:]))
