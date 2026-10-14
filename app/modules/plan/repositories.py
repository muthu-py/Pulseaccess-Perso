"""Plan module repository — persistence for plans."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.community.models import Community
from app.modules.plan.models import Plan


class PlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_community(self, community_id: uuid.UUID) -> Community | None:
        result = await self._session.execute(
            select(Community).where(Community.id == community_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, plan_id: uuid.UUID) -> Plan | None:
        result = await self._session.execute(select(Plan).where(Plan.id == plan_id))
        return result.scalar_one_or_none()

    async def list_by_community(
        self,
        community_id: uuid.UUID,
        *,
        active_only: bool,
    ) -> Sequence[Plan]:
        stmt = select(Plan).where(Plan.community_id == community_id)
        if active_only:
            stmt = stmt.where(Plan.is_active.is_(True))
        stmt = stmt.order_by(Plan.price_paise, Plan.created_at)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def exists_by_name(
        self,
        community_id: uuid.UUID,
        name: str,
        exclude_id: uuid.UUID | None = None,
    ) -> bool:
        stmt = (
            select(func.count())
            .select_from(Plan)
            .where(Plan.community_id == community_id, Plan.name == name)
        )
        if exclude_id is not None:
            stmt = stmt.where(Plan.id != exclude_id)
        result = await self._session.execute(stmt)
        return result.scalar_one() > 0

    async def create(self, plan: Plan) -> Plan:
        self._session.add(plan)
        await self._session.flush()
        return plan

    async def save(self, plan: Plan) -> Plan:
        await self._session.flush()
        await self._session.refresh(plan)
        return plan
