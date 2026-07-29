"""Telegram infrastructure exceptions.

Translates Telegram Bot API errors into domain-level exceptions
so that business services never inspect raw HTTP responses (Doc 04 §16).
"""


class TelegramException(Exception):
    """Base exception for all Telegram infrastructure errors."""

    def __init__(self, message: str = "Telegram API error") -> None:
        self.message = message
        super().__init__(self.message)


class TelegramAuthenticationException(TelegramException):
    """Bot token is invalid or revoked (HTTP 401)."""

    def __init__(self, message: str = "Telegram authentication failed") -> None:
        super().__init__(message)


class TelegramPermissionException(TelegramException):
    """Bot lacks required permissions in the chat (HTTP 403)."""

    def __init__(self, message: str = "Telegram permission denied") -> None:
        super().__init__(message)


class TelegramRateLimitException(TelegramException):
    """Telegram rate limit exceeded (HTTP 429)."""

    def __init__(
        self,
        message: str = "Telegram rate limit exceeded",
        retry_after: int = 0,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(message)


class TelegramTimeoutException(TelegramException):
    """HTTP request to Telegram timed out."""

    def __init__(self, message: str = "Telegram request timed out") -> None:
        super().__init__(message)


class TelegramNotFoundException(TelegramException):
    """Requested Telegram resource was not found (HTTP 404)."""

    def __init__(self, message: str = "Telegram resource not found") -> None:
        super().__init__(message)


class TelegramWebhookException(TelegramException):
    """Webhook verification or processing failed."""

    def __init__(self, message: str = "Telegram webhook error") -> None:
        super().__init__(message)


class TelegramUnknownException(TelegramException):
    """Unrecognized Telegram error."""

    def __init__(self, message: str = "Unknown Telegram error") -> None:
        super().__init__(message)
