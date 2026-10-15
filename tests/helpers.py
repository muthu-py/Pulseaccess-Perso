"""Shared builders for plan / payment tests: real tokens, real rows."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.infrastructure.security.jwt_service import JWTService
from app.modules.community.models import Community
from app.modules.member.models import Member
from app.modules.telegram.enums import TelegramConnectionStatus
from app.modules.telegram_connect.enums import OwnerType
from app.modules.telegram_connect.models import TelegramAccount


def auth_headers(subject: uuid.UUID, role: str) -> dict:
    token = JWTService(get_settings()).create_access_token(
        subject=str(subject), extra_claims={"role": role},
    )
    return {"Authorization": f"Bearer {token}"}


async def make_community(
    db: AsyncSession,
    creator_id: uuid.UUID,
    *,
    name: str = "Java Masters",
    connected: bool = True,
) -> Community:
    community = Community(
        creator_id=creator_id,
        name=name,
        telegram_chat_id=f"-100{uuid.uuid4().int % 10**10}" if connected else None,
        telegram_connection_status=(
            TelegramConnectionStatus.CONNECTED.value
            if connected
            else TelegramConnectionStatus.NOT_CONNECTED.value
        ),
    )
    db.add(community)
    await db.flush()
    return community


async def make_member(db: AsyncSession, *, telegram: bool = True) -> Member:
    suffix = uuid.uuid4().hex[:8]
    phone = f"+9198{uuid.uuid4().int % 10**8:08d}"
    member = Member(name=f"Member {suffix}", phone=phone, email=f"{suffix}@example.com")
    db.add(member)
    await db.flush()
    if telegram:
        db.add(TelegramAccount(
            owner_type=OwnerType.MEMBER.value,
            owner_id=member.id,
            telegram_user_id=str(uuid.uuid4().int % 10**9),
            phone=phone,
        ))
        await db.flush()
    return member
