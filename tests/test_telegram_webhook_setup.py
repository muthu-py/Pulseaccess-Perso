import httpx
import pytest
from httpx import AsyncClient

from app.core.config import Settings, get_settings
from app.infrastructure.telegram.telegram_driver import TelegramDriver
from app.main import app as fastapi_app
from app.infrastructure.telegram import telegram_constants as itc
from app.modules.telegram import constants as tc

WEBHOOK_SECRET = "test_telegram_webhook_secret"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        DATABASE_URL="postgresql://user:pass@localhost:5432/db",
        JWT_SECRET_KEY="test_secret_key_at_least_32_characters_long",
        OTP_HASH_SECRET="test_otp_secret_at_least_32_characters_long",
        TELEGRAM_BOT_TOKEN="123:ABC",
        TELEGRAM_WEBHOOK_SECRET=WEBHOOK_SECRET,
    )


# ── Driver ──────────────────────────────────────────────────────────────


async def test_set_webhook_sends_secret_and_allowed_updates(settings: Settings, monkeypatch):
    captured: dict = {}

    async def mock_post(self, url, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return httpx.Response(200, json={"ok": True, "result": True}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    driver = TelegramDriver(settings)
    await driver.set_webhook(
        "https://abc.ngrok-free.app" + tc.WEBHOOK_PATH,
        secret_token=WEBHOOK_SECRET,
        allowed_updates=itc.WEBHOOK_ALLOWED_UPDATES,
    )

    assert captured["url"] == "https://api.telegram.org/bot123:ABC/setWebhook"
    assert captured["json"] == {
        "url": "https://abc.ngrok-free.app/api/v1/webhooks/telegram",
        "secret_token": WEBHOOK_SECRET,
        "allowed_updates": ["message", "my_chat_member", "chat_member", "chat_join_request"],
        "drop_pending_updates": False,
    }


async def test_get_webhook_info_maps_response(settings: Settings, monkeypatch):
    async def mock_post(self, url, **kwargs):
        assert url.endswith("/getWebhookInfo")
        return httpx.Response(
            200,
            json={
                "ok": True,
                "result": {
                    "url": "https://abc.ngrok-free.app/api/v1/webhooks/telegram",
                    "has_custom_certificate": False,
                    "pending_update_count": 2,
                    "allowed_updates": ["message", "my_chat_member"],
                },
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    info = await TelegramDriver(settings).get_webhook_info()
    assert info.url.endswith(tc.WEBHOOK_PATH)
    assert info.pending_update_count == 2
    assert info.allowed_updates == ["message", "my_chat_member"]


# ── Webhook endpoint auth ───────────────────────────────────────────────


@pytest.fixture
async def webhook_client(async_client: AsyncClient, settings: Settings) -> AsyncClient:
    fastapi_app.dependency_overrides[get_settings] = lambda: settings
    return async_client


async def test_webhook_rejects_wrong_secret(webhook_client: AsyncClient):
    resp = await webhook_client.post(
        tc.WEBHOOK_PATH,
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
    )
    assert resp.status_code == 401


async def test_webhook_rejects_missing_secret_header(webhook_client: AsyncClient):
    resp = await webhook_client.post(tc.WEBHOOK_PATH, json={"update_id": 1})
    assert resp.status_code == 401


async def test_webhook_rejects_when_secret_not_configured(
    async_client: AsyncClient, settings: Settings
):
    unconfigured = settings.model_copy(update={"TELEGRAM_WEBHOOK_SECRET": ""})
    fastapi_app.dependency_overrides[get_settings] = lambda: unconfigured
    resp = await async_client.post(
        tc.WEBHOOK_PATH,
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": ""},
    )
    assert resp.status_code == 401


async def test_webhook_accepts_correct_secret(webhook_client: AsyncClient):
    resp = await webhook_client.post(
        tc.WEBHOOK_PATH,
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": WEBHOOK_SECRET},
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
