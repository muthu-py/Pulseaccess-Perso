"""Member module FastAPI dependencies."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_email_service, get_jwt_service, get_security_service
from app.core.config import Settings, get_settings
from app.core.security import SecurityService
from app.infrastructure.database.session import get_db
from app.infrastructure.email.smtp_email_service import SMTPEmailService
from app.infrastructure.security.jwt_service import JWTService
from app.modules.member.repositories import MemberRepository
from app.modules.member.services import MemberService
from app.modules.telegram_connect.dependencies import get_telegram_connect_service
from app.modules.telegram_connect.services import TelegramConnectService


def get_member_service(
    session: AsyncSession = Depends(get_db),
    security_service: SecurityService = Depends(get_security_service),
    jwt_service: JWTService = Depends(get_jwt_service),
    email_service: SMTPEmailService = Depends(get_email_service),
    telegram_connect: TelegramConnectService = Depends(get_telegram_connect_service),
    settings: Settings = Depends(get_settings),
) -> MemberService:
    return MemberService(
        repository=MemberRepository(session=session),
        security_service=security_service,
        jwt_service=jwt_service,
        email_service=email_service,
        telegram_connect=telegram_connect,
        settings=settings,
    )
