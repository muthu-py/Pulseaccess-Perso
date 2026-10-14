"""Member module request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.phone import is_valid_phone, normalize_phone


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    phone: str
    email: str
    is_active: bool
    created_at: datetime
    telegram_connected: bool = False


class MemberRegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: str = Field(..., description="With country code, e.g. +919876543210")

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, value: str) -> str:
        if not is_valid_phone(value):
            raise ValueError("Phone must include the country code, e.g. +919876543210")
        return normalize_phone(value)


class MemberRequestOTPRequest(BaseModel):
    email: EmailStr


class MemberRequestOTPResponse(BaseModel):
    message: str = "If an account exists, a login code has been sent."


class MemberVerifyOTPRequest(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6)


class MemberTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
