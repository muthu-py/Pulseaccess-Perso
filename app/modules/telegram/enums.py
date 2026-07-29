"""Telegram module enumerations.

Defines all valid state values for community connections,
telegram operations, and operation statuses.
"""

import enum


class TelegramConnectionStatus(str, enum.Enum):
    """Lifecycle states for a community's Telegram connection."""

    NOT_CONNECTED = "NOT_CONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    NEEDS_ATTENTION = "NEEDS_ATTENTION"
    DISCONNECTED = "DISCONNECTED"


class TelegramOperationType(str, enum.Enum):
    """Types of asynchronous Telegram operations."""

    CREATE_INVITE = "CREATE_INVITE"
    REMOVE_MEMBER = "REMOVE_MEMBER"
    VERIFY_CONNECTION = "VERIFY_CONNECTION"
    SYNC_MEMBER = "SYNC_MEMBER"


class TelegramOperationStatus(str, enum.Enum):
    """Execution states for a queued Telegram operation."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    RETRYING = "RETRYING"
    FAILED = "FAILED"
