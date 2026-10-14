"""Member module service — registration and passwordless login for members."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from app.core.config import Settings
from app.core.exceptions import InvalidOTPError, OTPAttemptLimitExceededError, OTPExpiredError
from app.core.logging import get_logger
from app.core.security import SecurityService
from app.infrastructure.email.email_interface import EmailService
from app.infrastructure.security.jwt_service import JWTService
from app.modules.member.exceptions import (
    InactiveMemberError,
    MemberAlreadyExistsError,
    MemberNotFoundError,
)
from app.modules.member.repositories import MemberRepository
from app.modules.member.schemas import (
    MemberRegisterRequest,
    MemberRequestOTPRequest,
    MemberRequestOTPResponse,
    MemberResponse,
    MemberTokenResponse,
    MemberVerifyOTPRequest,
)
from app.modules.telegram_connect.enums import OwnerType
from app.modules.telegram_connect.services import TelegramConnectService

logger = get_logger(__name__)


def _ensure_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class MemberService:
    """Orchestrates member registration and login."""

    def __init__(
        self,
        repository: MemberRepository,
        security_service: SecurityService,
        jwt_service: JWTService,
        email_service: EmailService,
        telegram_connect: TelegramConnectService,
        settings: Settings,
    ) -> None:
        self._repo = repository
        self._security = security_service
        self._jwt = jwt_service
        self._email = email_service
        self._telegram_connect = telegram_connect
        self._settings = settings

    async def register(self, request: MemberRegisterRequest) -> MemberResponse:
        if await self._repo.exists_email(request.email):
            raise MemberAlreadyExistsError("A member with this email already exists.")
        if await self._repo.exists_phone(request.phone):
            raise MemberAlreadyExistsError("A member with this phone number already exists.")

        member = await self._repo.create(
            name=request.name,
            phone=request.phone,
            email=request.email,
        )
        logger.info("Member registered: %s", member.id)
        return MemberResponse.model_validate(member)

    async def request_otp(self, request: MemberRequestOTPRequest) -> MemberRequestOTPResponse:
        """Send a login code. Always returns the same response (no account enumeration)."""
        member = await self._repo.get_by_email(request.email)
        if member is None or not member.is_active:
            return MemberRequestOTPResponse()

        await self._repo.invalidate_active_otps(member.id)

        otp_code = self._security.generate_otp(length=self._settings.OTP_LENGTH)
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=self._settings.OTP_EXPIRY_MINUTES,
        )
        await self._repo.create_otp(member.id, self._security.hash_value(otp_code), expires_at)

        await self._email.send_login_otp(
            to_email=member.email,
            otp_code=otp_code,
            creator_name=member.name,
        )
        logger.info("OTP requested for member %s", member.id)
        return MemberRequestOTPResponse()

    async def verify_otp(self, request: MemberVerifyOTPRequest) -> MemberTokenResponse:
        member = await self._repo.get_by_email(request.email)
        if member is None:
            raise InvalidOTPError()
        if not member.is_active:
            raise InactiveMemberError()

        otp = await self._repo.get_active_otp(member.id)
        if otp is None:
            raise InvalidOTPError()
        if _ensure_utc(otp.expires_at) < datetime.now(timezone.utc):
            raise OTPExpiredError()
        if otp.attempts >= self._settings.OTP_MAX_ATTEMPTS:
            raise OTPAttemptLimitExceededError()

        if not self._security.verify_hash(request.otp_code, otp.otp_hash):
            await self._repo.increment_otp_attempts(otp.id)
            # Keep the failed attempt even though the request ends in an error.
            await self._repo.commit()
            raise InvalidOTPError()

        await self._repo.mark_otp_used(otp.id)

        access_token = self._jwt.create_access_token(
            subject=str(member.id),
            extra_claims={"role": "member"},
        )
        logger.info("Member login success: %s", member.id)
        return MemberTokenResponse(access_token=access_token)

    async def get_me(self, member_id: uuid.UUID) -> MemberResponse:
        member = await self._repo.get_by_id(member_id)
        if member is None:
            raise MemberNotFoundError()
        response = MemberResponse.model_validate(member)
        response.telegram_connected = await self._telegram_connect.is_connected(
            OwnerType.MEMBER,
            member_id,
        )
        return response
