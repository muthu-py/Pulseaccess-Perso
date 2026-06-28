from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


# ======================================================================
# Base Exception
# ======================================================================

class PulseAccessException(Exception):
    """Base exception for all domain errors in PulseAccess."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.__class__.message
        super().__init__(self.message)


# ======================================================================
# Creator Exceptions
# ======================================================================

class CreatorAlreadyExistsError(PulseAccessException):
    status_code = 409
    error_code = "CREATOR_ALREADY_EXISTS"
    message = "A creator with this email or username already exists."


class CreatorNotFoundError(PulseAccessException):
    status_code = 404
    error_code = "CREATOR_NOT_FOUND"
    message = "Creator not found."


class InactiveCreatorError(PulseAccessException):
    status_code = 403
    error_code = "INACTIVE_CREATOR"
    message = "This account is inactive."


# ======================================================================
# OTP Exceptions
# ======================================================================

class InvalidOTPError(PulseAccessException):
    status_code = 401
    error_code = "INVALID_OTP"
    message = "The OTP provided is invalid."


class OTPExpiredError(PulseAccessException):
    status_code = 401
    error_code = "OTP_EXPIRED"
    message = "The OTP has expired. Please request a new one."


class OTPAttemptLimitExceededError(PulseAccessException):
    status_code = 429
    error_code = "OTP_ATTEMPT_LIMIT_EXCEEDED"
    message = "Too many incorrect attempts. Please request a new OTP."


# ======================================================================
# Refresh Token Exceptions
# ======================================================================

class InvalidRefreshTokenError(PulseAccessException):
    status_code = 401
    error_code = "INVALID_REFRESH_TOKEN"
    message = "The refresh token is invalid."


class RefreshTokenExpiredError(PulseAccessException):
    status_code = 401
    error_code = "REFRESH_TOKEN_EXPIRED"
    message = "The refresh token has expired. Please log in again."


class RefreshTokenRevokedError(PulseAccessException):
    status_code = 401
    error_code = "REFRESH_TOKEN_REVOKED"
    message = "The refresh token has been revoked."


# ======================================================================
# Global Exception Handler
# ======================================================================

def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI application."""

    @app.exception_handler(PulseAccessException)
    async def pulse_access_exception_handler(
        request: Request,
        exc: PulseAccessException,
    ) -> JSONResponse:
        logger.warning(
            "Domain exception: %s — %s (path=%s)",
            exc.error_code,
            exc.message,
            request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.message,
                "error_code": exc.error_code,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception(
            "Unhandled exception on %s %s",
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "An unexpected error occurred.",
                "error_code": "INTERNAL_ERROR",
            },
        )
