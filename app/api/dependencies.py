from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import SecurityService
from app.infrastructure.database.session import get_db
from app.infrastructure.email.smtp_email_service import SMTPEmailService
from app.infrastructure.security.cookie_service import CookieService
from app.infrastructure.security.jwt_service import JWTService
from app.infrastructure.security.session_service import SessionService
from app.modules.auth.repositories import (
    CreatorRepository,
    OTPRepository,
    RefreshTokenRepository,
)
from app.modules.auth.services import AuthService

# Existing module services — preserved
from app.modules.community.services import CommunityService
from app.modules.plan.services import PlanService
from app.modules.subscription.services import SubscriptionService
from app.infrastructure.telegram.telegram_interface import TelegramService
from app.infrastructure.telegram.telegram_stub import TelegramStub
from app.infrastructure.razorpay.razorpay_interface import RazorpayService
from app.infrastructure.razorpay.razorpay_stub import RazorpayStub


# ======================================================================
# Infrastructure Dependencies
# ======================================================================

def get_security_service(
    settings: Settings = Depends(get_settings),
) -> SecurityService:
    return SecurityService(otp_hash_secret=settings.OTP_HASH_SECRET)


def get_jwt_service(
    settings: Settings = Depends(get_settings),
) -> JWTService:
    return JWTService(settings=settings)


def get_cookie_service(
    settings: Settings = Depends(get_settings),
) -> CookieService:
    return CookieService(settings=settings)


def get_email_service(
    settings: Settings = Depends(get_settings),
) -> SMTPEmailService:
    return SMTPEmailService(settings=settings)


# ======================================================================
# Repository Dependencies
# ======================================================================

def get_creator_repository(
    session: AsyncSession = Depends(get_db),
) -> CreatorRepository:
    return CreatorRepository(session=session)


def get_otp_repository(
    session: AsyncSession = Depends(get_db),
) -> OTPRepository:
    return OTPRepository(session=session)


def get_refresh_token_repository(
    session: AsyncSession = Depends(get_db),
) -> RefreshTokenRepository:
    return RefreshTokenRepository(session=session)


# ======================================================================
# Session Service (depends on JWT, Security, Cookie, RefreshTokenRepo)
# ======================================================================

def get_session_service(
    jwt_service: JWTService = Depends(get_jwt_service),
    security_service: SecurityService = Depends(get_security_service),
    cookie_service: CookieService = Depends(get_cookie_service),
    refresh_token_repo: RefreshTokenRepository = Depends(get_refresh_token_repository),
    settings: Settings = Depends(get_settings),
) -> SessionService:
    return SessionService(
        jwt_service=jwt_service,
        security_service=security_service,
        cookie_service=cookie_service,
        refresh_token_repo=refresh_token_repo,
        settings=settings,
    )


# ======================================================================
# Auth Service (the top-level dependency)
# ======================================================================

def get_auth_service(
    creator_repo: CreatorRepository = Depends(get_creator_repository),
    otp_repo: OTPRepository = Depends(get_otp_repository),
    security_service: SecurityService = Depends(get_security_service),
    session_service: SessionService = Depends(get_session_service),
    cookie_service: CookieService = Depends(get_cookie_service),
    email_service: SMTPEmailService = Depends(get_email_service),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    return AuthService(
        creator_repo=creator_repo,
        otp_repo=otp_repo,
        security_service=security_service,
        session_service=session_service,
        cookie_service=cookie_service,
        email_service=email_service,
        settings=settings,
    )


# ======================================================================
# Other Module Services (unchanged stubs)
# ======================================================================

def get_community_service() -> CommunityService:
    return CommunityService()


def get_plan_service() -> PlanService:
    return PlanService()


def get_subscription_service() -> SubscriptionService:
    return SubscriptionService()


def get_telegram_service() -> TelegramService:
    return TelegramStub()


def get_razorpay_service() -> RazorpayService:
    return RazorpayStub()
