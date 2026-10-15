"""Plan module service — creators manage plans; members browse them.

Rules:
  - Only the creator who owns a community manages its plans.
  - Plans can be added only once the community is connected to Telegram,
    because a paid plan is useless without a group to grant access to.
  - Plans are deactivated, never deleted: payments and subscriptions
    reference them.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from app.core.logging import get_logger
from app.modules.community.models import Community
from app.modules.plan.exceptions import (
    CommunityNotConnectedError,
    DuplicatePlanNameError,
    PlanCommunityNotFoundError,
    PlanNotFoundError,
)
from app.modules.plan.models import Plan
from app.modules.plan.repositories import PlanRepository
from app.modules.plan.schemas import CreatePlanRequest, PlanResponse, UpdatePlanRequest
from app.modules.telegram.enums import TelegramConnectionStatus

logger = get_logger(__name__)


def _to_paise(rupees: Decimal) -> int:
    return int(rupees * 100)


def _is_connected(community: Community) -> bool:
    return community.telegram_connection_status == TelegramConnectionStatus.CONNECTED.value


class PlanService:
    def __init__(self, repository: PlanRepository) -> None:
        self._repo = repository

    # ── Creator ──────────────────────────────────────────────────────

    async def create_plan(
        self,
        creator_id: uuid.UUID,
        community_id: uuid.UUID,
        request: CreatePlanRequest,
    ) -> PlanResponse:
        community = await self._owned_community(community_id, creator_id)
        if not _is_connected(community):
            raise CommunityNotConnectedError()

        if await self._repo.exists_by_name(community_id, request.name):
            raise DuplicatePlanNameError()

        plan = Plan(
            community_id=community_id,
            name=request.name,
            description=request.description,
            price_paise=_to_paise(request.price),
            duration_days=request.duration_days,
            is_active=True,
        )
        try:
            plan = await self._repo.create(plan)
        except IntegrityError as exc:
            raise DuplicatePlanNameError() from exc

        logger.info("Plan %s created for community %s", plan.id, community_id)
        return PlanResponse.model_validate(plan, from_attributes=True)

    async def list_plans(
        self,
        creator_id: uuid.UUID,
        community_id: uuid.UUID,
    ) -> list[PlanResponse]:
        await self._owned_community(community_id, creator_id)
        plans = await self._repo.list_by_community(community_id, active_only=False)
        return [PlanResponse.model_validate(p, from_attributes=True) for p in plans]

    async def update_plan(
        self,
        creator_id: uuid.UUID,
        plan_id: uuid.UUID,
        request: UpdatePlanRequest,
    ) -> PlanResponse:
        plan = await self._owned_plan(plan_id, creator_id)
        fields = request.model_fields_set

        if "name" in fields and request.name is not None and request.name != plan.name:
            if await self._repo.exists_by_name(plan.community_id, request.name, exclude_id=plan.id):
                raise DuplicatePlanNameError()
            plan.name = request.name
        if "description" in fields:
            plan.description = request.description
        if "price" in fields and request.price is not None:
            plan.price_paise = _to_paise(request.price)
        if "duration_days" in fields and request.duration_days is not None:
            plan.duration_days = request.duration_days

        try:
            plan = await self._repo.save(plan)
        except IntegrityError as exc:
            raise DuplicatePlanNameError() from exc

        logger.info("Plan %s updated", plan.id)
        return PlanResponse.model_validate(plan, from_attributes=True)

    async def set_active(
        self,
        creator_id: uuid.UUID,
        plan_id: uuid.UUID,
        active: bool,
    ) -> PlanResponse:
        plan = await self._owned_plan(plan_id, creator_id)
        plan.is_active = active
        plan = await self._repo.save(plan)
        logger.info("Plan %s %s", plan.id, "activated" if active else "deactivated")
        return PlanResponse.model_validate(plan, from_attributes=True)

    # ── Member ───────────────────────────────────────────────────────

    async def list_available_plans(self, community_id: uuid.UUID) -> list[PlanResponse]:
        """Active plans members can buy right now."""
        community = await self._repo.get_community(community_id)
        if community is None or not community.is_active:
            raise PlanCommunityNotFoundError()
        if not _is_connected(community):
            return []
        plans = await self._repo.list_by_community(community_id, active_only=True)
        return [PlanResponse.model_validate(p, from_attributes=True) for p in plans]

    # ── Helpers ──────────────────────────────────────────────────────

    async def _owned_community(self, community_id: uuid.UUID, creator_id: uuid.UUID) -> Community:
        community = await self._repo.get_community(community_id)
        if community is None or community.creator_id != creator_id:
            raise PlanCommunityNotFoundError()
        return community

    async def _owned_plan(self, plan_id: uuid.UUID, creator_id: uuid.UUID) -> Plan:
        plan = await self._repo.get_by_id(plan_id)
        if plan is None:
            raise PlanNotFoundError()
        community = await self._repo.get_community(plan.community_id)
        if community is None or community.creator_id != creator_id:
            raise PlanNotFoundError()
        return plan
