import uuid
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.phone import is_valid_phone, normalize_phone

T = TypeVar("T")


# ======================================================================
# Base Response Wrappers
# ======================================================================

class BaseSuccessResponse(BaseModel, Generic[T]):
    """Standard success response envelope."""
    success: bool = True
    data: T


class BaseErrorResponse(BaseModel):
    """Standard error response envelope."""
    success: bool = False
    message: str
    error_code: str


# ======================================================================
# Creator
# ======================================================================

class CreatorResponse(BaseModel):
    """Public representation of a Creator."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    username: str
    email: str
    phone: str | None = None
    is_active: bool
    created_at: datetime


# ======================================================================
# Register
# ======================================================================

class RegisterRequest(BaseModel):
    """Payload for creating a new creator account."""
    name: str = Field(..., min_length=1, max_length=255)
    username: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr
    phone: str | None = Field(None, description="With country code, e.g. +919876543210")

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not is_valid_phone(value):
            raise ValueError("Phone must include the country code, e.g. +919876543210")
        return normalize_phone(value)


class UpdatePhoneRequest(BaseModel):
    """Payload for setting or changing the creator's phone number."""
    phone: str = Field(..., description="With country code, e.g. +919876543210")

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, value: str) -> str:
        if not is_valid_phone(value):
            raise ValueError("Phone must include the country code, e.g. +919876543210")
        return normalize_phone(value)


class RegisterResponse(BaseModel):
    """Response after successful registration."""
    model_config = ConfigDict(from_attributes=True)

    creator: CreatorResponse


# ======================================================================
# Request OTP
# ======================================================================

class RequestOTPRequest(BaseModel):
    """Payload for requesting a login OTP. Accepts email or username."""
    identifier: str = Field(..., min_length=1, max_length=255)


class RequestOTPResponse(BaseModel):
    """Response after OTP request — always generic to prevent account enumeration."""
    message: str = "If an account exists, a login code has been sent."


# ======================================================================
# Verify OTP
# ======================================================================

class VerifyOTPRequest(BaseModel):
    """Payload for verifying an OTP and logging in."""
    identifier: str = Field(..., min_length=1, max_length=255)
    otp_code: str = Field(..., min_length=6, max_length=6)


class VerifyOTPResponse(BaseModel):
    """Response after successful OTP verification — access token only, refresh in cookie."""
    access_token: str
    token_type: str = "bearer"


# ======================================================================
# Refresh
# ======================================================================

class RefreshResponse(BaseModel):
    """Response after token refresh — new access token."""
    access_token: str
    token_type: str = "bearer"


# ======================================================================
# Logout
# ======================================================================

class LogoutResponse(BaseModel):
    """Response after successful logout."""
    message: str = "Successfully logged out."
