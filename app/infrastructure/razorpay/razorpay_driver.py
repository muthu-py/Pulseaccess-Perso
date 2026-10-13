"""Razorpay HTTP client driver using httpx and native HMAC verification."""

import hashlib
import hmac
from typing import Any

import httpx

from app.core.config import Settings
from app.core.logging import get_logger
from app.infrastructure.razorpay.razorpay_exceptions import RazorpayAPIError
from app.infrastructure.razorpay.razorpay_interface import RazorpayClient

logger = get_logger(__name__)


class RazorpayDriver(RazorpayClient):
    """Production Razorpay client using async httpx and HMAC-SHA256."""

    def __init__(self, settings: Settings) -> None:
        self._key_id = settings.RAZORPAY_KEY_ID
        self._key_secret = settings.RAZORPAY_KEY_SECRET
        self._webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
        self._base_url = settings.RAZORPAY_API_BASE_URL.rstrip("/")
        self._auth = (self._key_id, self._key_secret)

    async def create_order(
        self,
        amount_paise: int,
        currency: str = "INR",
        receipt: str | None = None,
        notes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a payment order on Razorpay."""
        payload: dict[str, Any] = {
            "amount": amount_paise,
            "currency": currency,
        }
        if receipt:
            payload["receipt"] = receipt
        if notes:
            payload["notes"] = notes

        url = f"{self._base_url}/orders"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    auth=self._auth,
                )
                if response.is_error:
                    logger.error(
                        "Razorpay order creation failed: status=%s, body=%s",
                        response.status_code,
                        response.text,
                    )
                    raise RazorpayAPIError(
                        message=f"Razorpay order creation failed: {response.text}",
                        status_code=response.status_code,
                    )
                return response.json()
        except httpx.RequestError as exc:
            logger.error("HTTP network error communicating with Razorpay: %s", exc)
            raise RazorpayAPIError(message=f"Network error: {exc}") from exc

    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        signature: str,
    ) -> bool:
        """Cryptographically verify the HMAC-SHA256 webhook signature in constant time."""
        if not self._webhook_secret or not signature:
            logger.warning("Missing webhook secret or signature for verification")
            return False

        expected_signature = hmac.new(
            key=self._webhook_secret.encode("utf-8"),
            msg=payload_bytes,
            digestmod=hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature)

    async def fetch_payment(
        self,
        payment_id: str,
    ) -> dict[str, Any]:
        """Fetch details of a payment by its Razorpay payment ID."""
        url = f"{self._base_url}/payments/{payment_id}"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    url,
                    auth=self._auth,
                )
                if response.is_error:
                    logger.error(
                        "Razorpay fetch payment failed: status=%s, body=%s",
                        response.status_code,
                        response.text,
                    )
                    raise RazorpayAPIError(
                        message=f"Razorpay fetch payment failed: {response.text}",
                        status_code=response.status_code,
                    )
                return response.json()
        except httpx.RequestError as exc:
            logger.error("HTTP network error fetching payment from Razorpay: %s", exc)
            raise RazorpayAPIError(message=f"Network error: {exc}") from exc
