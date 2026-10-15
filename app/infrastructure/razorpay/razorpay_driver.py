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

    def __init__(
        self,
        settings: Settings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._key_id = settings.RAZORPAY_KEY_ID
        self._key_secret = settings.RAZORPAY_KEY_SECRET
        self._webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
        self._base_url = settings.RAZORPAY_API_BASE_URL.rstrip("/")
        self._auth = (self._key_id, self._key_secret)
        # Tests pass an httpx.MockTransport; production uses the network.
        self._transport = transport

    async def _request(
        self,
        method: str,
        path: str,
        action: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=15.0, transport=self._transport) as client:
                if method == "POST":
                    response = await client.post(url, json=payload, auth=self._auth)
                else:
                    response = await client.get(url, auth=self._auth)
                if response.is_error:
                    logger.error(
                        "Razorpay %s failed: status=%s, body=%s",
                        action,
                        response.status_code,
                        response.text,
                    )
                    raise RazorpayAPIError(
                        message=f"Razorpay {action} failed: {response.text}",
                        status_code=response.status_code,
                    )
                return response.json()
        except httpx.RequestError as exc:
            logger.error("HTTP network error during Razorpay %s: %s", action, exc)
            raise RazorpayAPIError(message=f"Network error: {exc}") from exc

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
        return await self._request("POST", "/orders", "order creation", payload)

    async def create_payment_link(
        self,
        *,
        amount_paise: int,
        currency: str,
        reference_id: str,
        description: str,
        customer: dict[str, str],
        expire_by: int,
        notes: dict[str, Any] | None = None,
        callback_url: str | None = None,
    ) -> dict[str, Any]:
        """Create a single-use Payment Link (hosted payment page)."""
        payload: dict[str, Any] = {
            "amount": amount_paise,
            "currency": currency,
            "accept_partial": False,
            "reference_id": reference_id,
            "description": description,
            "customer": customer,
            "expire_by": expire_by,
            # We hand the URL to the member ourselves.
            "notify": {"sms": False, "email": False},
            "reminder_enable": False,
            "notes": notes or {},
        }
        if callback_url:
            payload["callback_url"] = callback_url
            payload["callback_method"] = "get"
        return await self._request("POST", "/payment_links", "payment link creation", payload)

    async def fetch_payment_link(self, payment_link_id: str) -> dict[str, Any]:
        """Fetch a Payment Link (status, amount_paid, payments)."""
        return await self._request(
            "GET", f"/payment_links/{payment_link_id}", "fetch payment link",
        )

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
        return await self._request("GET", f"/payments/{payment_id}", "fetch payment")
