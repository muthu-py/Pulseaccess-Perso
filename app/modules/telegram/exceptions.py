"""Telegram module business exceptions.

All extend PulseAccessException so that the global exception handler
in app.core.exceptions returns consistent error payloads (Doc 05 §18).
"""

from app.core.exceptions import PulseAccessException


# ======================================================================
# Community Exceptions
# ======================================================================

class CommunityNotFoundError(PulseAccessException):
    status_code = 404
    error_code = "COMMUNITY_NOT_FOUND"
    message = "Community not found."


class CommunityAlreadyConnectedError(PulseAccessException):
    status_code = 409
    error_code = "COMMUNITY_ALREADY_CONNECTED"
    message = "This community is already connected to a Telegram group."


class CommunityNotConnectedError(PulseAccessException):
    status_code = 409
    error_code = "COMMUNITY_NOT_CONNECTED"
    message = "This community is not connected to Telegram."


class UnauthorizedCommunityAccessError(PulseAccessException):
    status_code = 403
    error_code = "UNAUTHORIZED_COMMUNITY_ACCESS"
    message = "You do not own this community."


# ======================================================================
# Telegram Link Exceptions
# ======================================================================

class TelegramAccountAlreadyLinkedError(PulseAccessException):
    status_code = 409
    error_code = "TELEGRAM_ALREADY_LINKED"
    message = "A Telegram account is already linked to this member."


class TelegramNotLinkedError(PulseAccessException):
    status_code = 409
    error_code = "TELEGRAM_NOT_LINKED"
    message = "No Telegram account is linked. Please link first."


# ======================================================================
# Subscription / Access Exceptions
# ======================================================================

class SubscriptionInactiveError(PulseAccessException):
    status_code = 403
    error_code = "SUBSCRIPTION_INACTIVE"
    message = "An active subscription is required."


class MemberNotInCommunityError(PulseAccessException):
    status_code = 404
    error_code = "MEMBER_NOT_IN_COMMUNITY"
    message = "This member has never had a plan in this community."


class MemberPlanStillActiveError(PulseAccessException):
    status_code = 409
    error_code = "MEMBER_PLAN_ACTIVE"
    message = "This member still has an active plan. They can be removed once it expires."


class BotCannotRemoveMemberError(PulseAccessException):
    status_code = 409
    error_code = "BOT_CANNOT_REMOVE_MEMBER"
    message = (
        "The bot couldn't remove this member. Make sure it is an admin of the "
        "group with the Ban users permission."
    )


# ======================================================================
# Connection Code Exceptions
# ======================================================================

# ======================================================================
# Telegram Operation Exceptions
# ======================================================================

class TelegramOperationFailedError(PulseAccessException):
    status_code = 503
    error_code = "TELEGRAM_OPERATION_FAILED"
    message = "Telegram operation could not be completed at this time."
