"""Community module repository — persistence layer.

Handles all database operations for the communities table.
Contains NO business logic, NO external HTTP calls.

Every query is scoped by creator_id to enforce ownership isolation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.community.models import Community


class CommunityRepository:
    """Data access layer for Community persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, community: Community) -> Community:
        """Insert a new community and flush to populate defaults."""
        self._session.add(community)
        await self._session.flush()
        return community

    async def get_by_id(
        self,
        community_id: uuid.UUID,
        creator_id: uuid.UUID,
    ) -> Community | None:
        """Fetch a community scoped by ownership."""
        stmt = select(Community).where(
            Community.id == community_id,
            Community.creator_id == creator_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active(
        self,
        creator_id: uuid.UUID,
        offset: int,
        limit: int,
    ) -> Sequence[Community]:
        """Return active communities for a creator, newest first."""
        stmt = (
            select(Community)
            .where(
                Community.creator_id == creator_id,
                Community.is_active.is_(True),
            )
            .order_by(Community.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_active(self, creator_id: uuid.UUID) -> int:
        """Total active community count for pagination."""
        stmt = (
            select(func.count())
            .select_from(Community)
            .where(
                Community.creator_id == creator_id,
                Community.is_active.is_(True),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def list_inactive(
        self,
        creator_id: uuid.UUID,
        offset: int,
        limit: int,
    ) -> Sequence[Community]:
        """Return inactive communities for a creator, newest first."""
        stmt = (
            select(Community)
            .where(
                Community.creator_id == creator_id,
                Community.is_active.is_(False),
            )
            .order_by(Community.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_inactive(self, creator_id: uuid.UUID) -> int:
        """Total inactive community count for pagination."""
        stmt = (
            select(func.count())
            .select_from(Community)
            .where(
                Community.creator_id == creator_id,
                Community.is_active.is_(False),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def update(
        self,
        community_id: uuid.UUID,
        creator_id: uuid.UUID,
        values: dict,
    ) -> None:
        """Update community fields, scoped by ownership."""
        values["updated_at"] = datetime.now(timezone.utc)
        stmt = (
            update(Community)
            .where(
                Community.id == community_id,
                Community.creator_id == creator_id,
            )
            .values(**values)
        )
        await self._session.execute(stmt)

    async def activate(
        self,
        community_id: uuid.UUID,
        creator_id: uuid.UUID,
    ) -> None:
        """Set is_active = True."""
        await self.update(community_id, creator_id, {"is_active": True})

    async def deactivate(
        self,
        community_id: uuid.UUID,
        creator_id: uuid.UUID,
    ) -> None:
        """Set is_active = False. Telegram columns remain untouched."""
        await self.update(community_id, creator_id, {"is_active": False})

    async def exists_by_name(
        self,
        creator_id: uuid.UUID,
        name: str,
        exclude_id: uuid.UUID | None = None,
    ) -> bool:
        """Check if a community with the given name already exists for this creator."""
        stmt = (
            select(func.count())
            .select_from(Community)
            .where(
                Community.creator_id == creator_id,
                Community.name == name,
            )
        )
        if exclude_id is not None:
            stmt = stmt.where(Community.id != exclude_id)
        result = await self._session.execute(stmt)
        return result.scalar_one() > 0

    async def has_pending_telegram(
        self,
        creator_id: uuid.UUID,
        exclude_id: uuid.UUID | None = None,
    ) -> bool:
        """True if the creator has an active community not yet linked to a chat."""
        stmt = (
            select(func.count())
            .select_from(Community)
            .where(
                Community.creator_id == creator_id,
                Community.is_active.is_(True),
                Community.telegram_chat_id.is_(None),
            )
        )
        if exclude_id is not None:
            stmt = stmt.where(Community.id != exclude_id)
        result = await self._session.execute(stmt)
        return result.scalar_one() > 0
