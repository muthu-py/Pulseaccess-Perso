"""Plan module business exceptions."""

from app.core.exceptions import PulseAccessException


class PlanNotFoundError(PulseAccessException):
    status_code = 404
    error_code = "PLAN_NOT_FOUND"
    message = "Plan not found."


class PlanCommunityNotFoundError(PulseAccessException):
    """Returned for missing communities and ones the creator doesn't own."""

    status_code = 404
    error_code = "COMMUNITY_NOT_FOUND"
    message = "Community not found."


class CommunityNotConnectedError(PulseAccessException):
    status_code = 409
    error_code = "COMMUNITY_NOT_CONNECTED"
    message = "Connect this community to its Telegram group before adding plans."


class DuplicatePlanNameError(PulseAccessException):
    status_code = 409
    error_code = "DUPLICATE_PLAN_NAME"
    message = "This community already has a plan with this name."
