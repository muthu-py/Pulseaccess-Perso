import hashlib
import hmac
import json
import pytest
import httpx

from app.core.config import Settings
from app.infrastructure.razorpay.razorpay_driver import RazorpayDriver
from app.infrastructure.razorpay.razorpay_exceptions import RazorpayAPIError


@pytest.fixture
def dummy_settings() -> Settings:
    return Settings(
        DATABASE_URL="postgresql://user:pass@localhost:5432/db",
        JWT_SECRET_KEY="test_secret_key_at_least_32_characters_long",
        OTP_HASH_SECRET="test_otp_secret_at_least_32_characters_long",
        RAZORPAY_KEY_ID="rzp_test_samplekey123",
        RAZORPAY_KEY_SECRET="samplekeysecret456",
        RAZORPAY_WEBHOOK_SECRET="samplewebhooksecret789",
    )


def test_verify_webhook_signature_valid(dummy_settings: Settings):
    driver = RazorpayDriver(dummy_settings)
    payload = json.dumps({"event": "payment.captured", "payment_id": "pay_123"}).encode("utf-8")
    
    # Compute real HMAC signature
    signature = hmac.new(
        key=dummy_settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    ).hexdigest()

    assert driver.verify_webhook_signature(payload, signature) is True


def test_verify_webhook_signature_tampered_payload(dummy_settings: Settings):
    driver = RazorpayDriver(dummy_settings)
    payload = b'{"event": "payment.captured"}'
    signature = hmac.new(
        key=dummy_settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    ).hexdigest()

    tampered_payload = b'{"event": "payment.captured", "extra": "hacked"}'
    assert driver.verify_webhook_signature(tampered_payload, signature) is False


def test_verify_webhook_signature_invalid_sig(dummy_settings: Settings):
    driver = RazorpayDriver(dummy_settings)
    payload = b'{"event": "payment.captured"}'
    assert driver.verify_webhook_signature(payload, "invalid_forged_signature") is False


def test_verify_webhook_signature_missing_secret():
    settings_without_secret = Settings(
        DATABASE_URL="postgresql://user:pass@localhost:5432/db",
        JWT_SECRET_KEY="test_secret_key_at_least_32_characters_long",
        OTP_HASH_SECRET="test_otp_secret_at_least_32_characters_long",
        RAZORPAY_WEBHOOK_SECRET="",
    )
    driver = RazorpayDriver(settings_without_secret)
    assert driver.verify_webhook_signature(b"{}", "some_sig") is False


@pytest.mark.asyncio
async def test_create_order_success(dummy_settings: Settings, monkeypatch):
    driver = RazorpayDriver(dummy_settings)

    async def mock_post(self, url, **kwargs):
        assert url == "https://api.razorpay.com/v1/orders"
        json_data = kwargs.get("json", {})
        assert json_data["amount"] == 50000
        assert json_data["currency"] == "INR"
        return httpx.Response(
            status_code=200,
            json={"id": "order_test_999", "amount": 50000, "status": "created"},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    order = await driver.create_order(
        amount_paise=50000,
        currency="INR",
        receipt="rcpt_001",
        notes={"plan": "pro"},
    )
    assert order["id"] == "order_test_999"
    assert order["status"] == "created"


@pytest.mark.asyncio
async def test_create_order_failure(dummy_settings: Settings, monkeypatch):
    driver = RazorpayDriver(dummy_settings)

    async def mock_post(self, url, **kwargs):
        return httpx.Response(
            status_code=400,
            text='{"error": {"description": "Bad Request"}}',
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    with pytest.raises(RazorpayAPIError) as exc_info:
        await driver.create_order(amount_paise=50000)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_fetch_payment_success(dummy_settings: Settings, monkeypatch):
    driver = RazorpayDriver(dummy_settings)

    async def mock_get(self, url, **kwargs):
        assert url == "https://api.razorpay.com/v1/payments/pay_abc123"
        return httpx.Response(
            status_code=200,
            json={"id": "pay_abc123", "amount": 50000, "status": "captured"},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    payment = await driver.fetch_payment("pay_abc123")
    assert payment["id"] == "pay_abc123"
    assert payment["status"] == "captured"
