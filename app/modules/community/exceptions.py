"""Community module business exceptions.

All extend PulseAccessException so that the global exception handler
returns consistent error payloads.
"""

from app.core.exceptions import PulseAccessException


class CommunityNotFoundError(PulseAccessException):
    status_code = 404
    error_code = "COMMUNITY_NOT_FOUND"
    message = "Community not found."


class DuplicateCommunityNameError(PulseAccessException):
    status_code = 409
    error_code = "DUPLICATE_COMMUNITY_NAME"
    message = "A community with this name already exists."


class PendingTelegramConnectionError(PulseAccessException):
    """Only one community per creator may wait for its Telegram group.

    When the bot is added to a group, the creator's single unlinked
    community is the one it gets connected to.
    """

    status_code = 409
    error_code = "PENDING_TELEGRAM_CONNECTION"
    message = (
        "Connect your existing community to its Telegram group "
        "before creating another one."
    )


class CommunityOwnershipError(PulseAccessException):
    """Returns 404 to prevent leaking whether a community exists."""

    status_code = 404
    error_code = "COMMUNITY_NOT_FOUND"
    message = "Community not found."
