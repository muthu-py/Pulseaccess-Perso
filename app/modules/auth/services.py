from datetime import datetime, timedelta, timezone

from fastapi import Request, Response

from app.core.config import Settings
from app.core.exceptions import (
    CreatorAlreadyExistsError,
    InactiveCreatorError,
    InvalidOTPError,
    OTPAttemptLimitExceededError,
    OTPExpiredError,
)
from app.core.logging import get_logger
from app.core.security import SecurityService
from app.infrastructure.email.email_interface import EmailService
from app.infrastructure.security.cookie_service import CookieService
from app.infrastructure.security.session_service import SessionService
from app.modules.auth.models import Creator
from app.modules.auth.repositories import CreatorRepository, OTPRepository
from app.modules.auth.schemas import (
    CreatorResponse,
    LogoutResponse,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
    RequestOTPRequest,
    RequestOTPResponse,
    VerifyOTPRequest,
    VerifyOTPResponse,
)

logger = get_logger(__name__)


class AuthService:
    """Orchestrates all authentication business logic."""

    def __init__(
        self,
        creator_repo: CreatorRepository,
        otp_repo: OTPRepository,
        security_service: SecurityService,
        session_service: SessionService,
        cookie_service: CookieService,
        email_service: EmailService,
        settings: Settings,
    ) -> None:
        self._creator_repo = creator_repo
        self._otp_repo = otp_repo
        self._security = security_service
        self._session_service = session_service
        self._cookie = cookie_service
        self._email = email_service
        self._settings = settings

    # ------------------------------------------------------------------
    # REGISTER
    # ------------------------------------------------------------------

    async def register(self, request: RegisterRequest) -> RegisterResponse:
        """
        Create a new creator account.

        Validates email and username uniqueness.
        """
        if await self._creator_repo.exists_email(request.email):
            raise CreatorAlreadyExistsError("A creator with this email already exists.")

        if await self._creator_repo.exists_username(request.username):
            raise CreatorAlreadyExistsError("A creator with this username already exists.")

        creator = await self._creator_repo.create(
            name=request.name,
            username=request.username,
            email=request.email,
        )

        logger.info("Creator registered: %s (id=%s)", creator.username, creator.id)

        return RegisterResponse(
            creator=CreatorResponse.model_validate(creator),
        )

    # ------------------------------------------------------------------
    # REQUEST OTP
    # ------------------------------------------------------------------

    async def request_otp(self, request: RequestOTPRequest) -> RequestOTPResponse:
        """
        Generate and send a login OTP.

        If the creator doesn't exist, returns a generic success response
        to prevent account enumeration.
        """
        creator = await self._creator_repo.get_by_identifier(request.identifier)

        if creator is None:
            # Never reveal whether account exists
            return RequestOTPResponse()

        if not creator.is_active:
            # Silent — don't reveal inactive status
            return RequestOTPResponse()

        # Invalidate any previous active OTP
        await self._otp_repo.invalidate_active(creator.id)

        # Generate secure OTP
        otp_code = self._security.generate_otp(length=self._settings.OTP_LENGTH)
        otp_hash = self._security.hash_value(otp_code)

        # Store hashed OTP
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=self._settings.OTP_EXPIRY_MINUTES,
        )
        await self._otp_repo.create(
            creator_id=creator.id,
            otp_hash=otp_hash,
            purpose="login",
            expires_at=expires_at,
        )

        # Send OTP email
        await self._email.send_login_otp(
            to_email=creator.email,
            otp_code=otp_code,
            creator_name=creator.name,
        )

        logger.info("OTP requested for creator %s", creator.id)

        return RequestOTPResponse()

    # ------------------------------------------------------------------
    # VERIFY OTP
    # ------------------------------------------------------------------

    async def verify_otp(
        self,
        request: VerifyOTPRequest,
        response: Response,
    ) -> VerifyOTPResponse:
        """
        Verify a login OTP and create a session.

        On success: returns access token in body, sets refresh token as HttpOnly cookie.
        On failure: increments attempt counter and raises appropriate exception.
        """
        creator = await self._creator_repo.get_by_identifier(request.identifier)
        if creator is None:
            raise InvalidOTPError()

        if not creator.is_active:
            raise InactiveCreatorError()

        # Load active OTP
        active_otp = await self._otp_repo.get_active(creator.id)

        if active_otp is None:
            raise InvalidOTPError()

        # Check expiry
        if active_otp.expires_at < datetime.now(timezone.utc):
            raise OTPExpiredError()

        # Check attempts
        if active_otp.attempts >= self._settings.OTP_MAX_ATTEMPTS:
            raise OTPAttemptLimitExceededError()

        if not self._security.verify_hash(request.otp_code, active_otp.otp_hash):
            await self._otp_repo.increment_attempts(active_otp.id)
            await self._otp_repo._session.commit()
            raise InvalidOTPError()

        # Mark OTP as used
        await self._otp_repo.mark_used(active_otp.id)

        # Create session — access token returned, refresh token set as cookie
        access_token = await self._session_service.create_session(
            creator_id=creator.id,
            response=response,
        )

        logger.info("OTP verified — login success for creator %s", creator.id)

        return VerifyOTPResponse(access_token=access_token)

    # ------------------------------------------------------------------
    # REFRESH
    # ------------------------------------------------------------------

    async def refresh(
        self,
        request: Request,
        response: Response,
    ) -> RefreshResponse:
        """
        Rotate the refresh token and issue a new access token.

        Reads the refresh token from the HttpOnly cookie.
        """
        raw_token = request.cookies.get(self._settings.COOKIE_NAME)
        if not raw_token:
            from app.core.exceptions import InvalidRefreshTokenError
            raise InvalidRefreshTokenError()

        access_token = await self._session_service.rotate_session(
            raw_token=raw_token,
            response=response,
        )

        logger.info("Refresh token rotated")

        return RefreshResponse(access_token=access_token)

    # ------------------------------------------------------------------
    # LOGOUT
    # ------------------------------------------------------------------

    async def logout(
        self,
        request: Request,
        response: Response,
    ) -> LogoutResponse:
        """
        Revoke the current refresh token and clear the cookie.
        """
        raw_token = request.cookies.get(self._settings.COOKIE_NAME)

        if raw_token:
            await self._session_service.revoke_session(raw_token)

        self._cookie.clear_refresh_cookie(response)

        logger.info("Logout completed")

        return LogoutResponse()
