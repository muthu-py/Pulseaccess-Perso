"""Plan module routers.

Creator endpoints manage a community's plans (creator Bearer token).
The member endpoint lists the plans a member can buy (member Bearer token).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_creator, get_current_member
from app.modules.auth.schemas import BaseSuccessResponse
from app.modules.plan.dependencies import get_plan_service
from app.modules.plan.schemas import CreatePlanRequest, PlanResponse, UpdatePlanRequest
from app.modules.plan.services import PlanService

router = APIRouter(tags=["plans"])


# ======================================================================
# Creator
# ======================================================================

@router.post(
    "/api/v1/communities/{community_id}/plans",
    response_model=BaseSuccessResponse[PlanResponse],
    status_code=201,
    summary="Create Plan",
    description=(
        "Adds a paid plan to a community you own. The community must be "
        "connected to its Telegram group. Price is in rupees."
    ),
)
async def create_plan(
    community_id: uuid.UUID,
    body: CreatePlanRequest,
    creator_id: uuid.UUID = Depends(get_current_creator),
    service: PlanService = Depends(get_plan_service),
) -> BaseSuccessResponse[PlanResponse]:
    return BaseSuccessResponse(data=await service.create_plan(creator_id, community_id, body))


@router.get(
    "/api/v1/communities/{community_id}/plans",
    response_model=BaseSuccessResponse[list[PlanResponse]],
    summary="List Plans (creator)",
    description="All plans of a community you own, including inactive ones.",
)
async def list_plans(
    community_id: uuid.UUID,
    creator_id: uuid.UUID = Depends(get_current_creator),
    service: PlanService = Depends(get_plan_service),
) -> BaseSuccessResponse[list[PlanResponse]]:
    return BaseSuccessResponse(data=await service.list_plans(creator_id, community_id))


@router.patch(
    "/api/v1/plans/{plan_id}",
    response_model=BaseSuccessResponse[PlanResponse],
    summary="Update Plan",
    description="Partial update. A price change applies to new payment links only.",
)
async def update_plan(
    plan_id: uuid.UUID,
    body: UpdatePlanRequest,
    creator_id: uuid.UUID = Depends(get_current_creator),
    service: PlanService = Depends(get_plan_service),
) -> BaseSuccessResponse[PlanResponse]:
    return BaseSuccessResponse(data=await service.update_plan(creator_id, plan_id, body))


@router.patch(
    "/api/v1/plans/{plan_id}/activate",
    response_model=BaseSuccessResponse[PlanResponse],
    summary="Activate Plan",
)
async def activate_plan(
    plan_id: uuid.UUID,
    creator_id: uuid.UUID = Depends(get_current_creator),
    service: PlanService = Depends(get_plan_service),
) -> BaseSuccessResponse[PlanResponse]:
    return BaseSuccessResponse(data=await service.set_active(creator_id, plan_id, True))


@router.patch(
    "/api/v1/plans/{plan_id}/deactivate",
    response_model=BaseSuccessResponse[PlanResponse],
    summary="Deactivate Plan",
    description="Stops new purchases. Existing subscriptions are unaffected.",
)
async def deactivate_plan(
    plan_id: uuid.UUID,
    creator_id: uuid.UUID = Depends(get_current_creator),
    service: PlanService = Depends(get_plan_service),
) -> BaseSuccessResponse[PlanResponse]:
    return BaseSuccessResponse(data=await service.set_active(creator_id, plan_id, False))


# ======================================================================
# Member
# ======================================================================

@router.get(
    "/api/v1/communities/{community_id}/plans/available",
    response_model=BaseSuccessResponse[list[PlanResponse]],
    summary="List Available Plans (member)",
    description="Active plans of a connected community, cheapest first.",
)
async def list_available_plans(
    community_id: uuid.UUID,
    _member_id: uuid.UUID = Depends(get_current_member),
    service: PlanService = Depends(get_plan_service),
) -> BaseSuccessResponse[list[PlanResponse]]:
    return BaseSuccessResponse(data=await service.list_available_plans(community_id))
