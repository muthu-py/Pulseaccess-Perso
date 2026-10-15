"""Payment status enums for orders and webhook events."""

from enum import Enum


class PaymentOrderStatus(str, Enum):
    """Lifecycle status of a payment order."""

    CREATED = "created"
    PAID = "paid"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class PaymentEventStatus(str, Enum):
    """Processing status of an incoming payment webhook event."""

    PROCESSED = "processed"
    ALREADY_PROCESSED = "already_processed"
    FAILED = "failed"
    IGNORED = "ignored"
