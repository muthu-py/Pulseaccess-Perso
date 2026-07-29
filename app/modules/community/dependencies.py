"""Community module FastAPI dependencies.

Provides dependency injection factories for the Community repository
and service. Follows the existing project pattern from
app/modules/telegram/dependencies.py.
"""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_db
from app.modules.community.repositories import CommunityRepository
from app.modules.community.services import CommunityService


def get_community_repository(
    session: AsyncSession = Depends(get_db),
) -> CommunityRepository:
    return CommunityRepository(session=session)


def get_community_service(
    repository: CommunityRepository = Depends(get_community_repository),
) -> CommunityService:
    return CommunityService(repository=repository)
