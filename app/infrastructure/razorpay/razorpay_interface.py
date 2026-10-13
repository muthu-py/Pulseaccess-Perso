"""Protocol defining the Razorpay client interface."""

from typing import Any, Protocol


class RazorpayClient(Protocol):
    """Protocol for Razorpay operations."""

    async def create_order(
        self,
        amount_paise: int,
        currency: str = "INR",
        receipt: str | None = None,
        notes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a payment order on Razorpay."""
        ...

    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        signature: str,
    ) -> bool:
        """Cryptographically verify the HMAC-SHA256 webhook signature."""
        ...

    async def fetch_payment(
        self,
        payment_id: str,
    ) -> dict[str, Any]:
        """Fetch details of a payment by its Razorpay payment ID."""
        ...


# Backward compatibility alias
RazorpayService = RazorpayClient
