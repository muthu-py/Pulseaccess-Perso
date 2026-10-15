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
        """Create a single-use Payment Link; returns id, short_url, status."""
        ...

    async def fetch_payment_link(self, payment_link_id: str) -> dict[str, Any]:
        """Fetch a Payment Link by id."""
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
