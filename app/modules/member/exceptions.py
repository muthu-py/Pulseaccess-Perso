"""Member module business exceptions."""

from app.core.exceptions import PulseAccessException


class MemberAlreadyExistsError(PulseAccessException):
    status_code = 409
    error_code = "MEMBER_ALREADY_EXISTS"
    message = "A member with this email or phone already exists."


class MemberNotFoundError(PulseAccessException):
    status_code = 404
    error_code = "MEMBER_NOT_FOUND"
    message = "Member not found."


class InactiveMemberError(PulseAccessException):
    status_code = 403
    error_code = "INACTIVE_MEMBER"
    message = "This account is inactive."
