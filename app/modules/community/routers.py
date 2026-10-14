"""Community module routers — REST API endpoints.

Defines all Community CRUD endpoints for authenticated creators.
Routers are thin: validate → authenticate → delegate to service.

Auth guard: Bearer JWT via get_current_creator on every endpoint.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_current_creator
from app.core.logging import get_logger
from app.modules.auth.schemas import BaseSuccessResponse
from app.modules.community.dependencies import get_community_service
from app.modules.community.schemas import (
    CommunityListResponse,
    CommunityResponse,
    CreateCommunityRequest,
    UpdateCommunityRequest,
)
from app.modules.community.services import CommunityService
from app.modules.telegram_connect.dependencies import require_creator_telegram

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/communities", tags=["communities"])


# ======================================================================
# Create
# ======================================================================

@router.post(
    "",
    response_model=BaseSuccessResponse[CommunityResponse],
    status_code=201,
    summary="Create Community",
    description=(
        "Creates a new community for the authenticated creator. "
        "Community name must be unique per creator (3–100 characters). "
        "The creator must have connected Telegram first."
    ),
)
async def create_community(
    body: CreateCommunityRequest,
    creator_id: uuid.UUID = Depends(require_creator_telegram),
    service: CommunityService = Depends(get_community_service),
) -> BaseSuccessResponse[CommunityResponse]:
    """Create a new community."""
    result = await service.create_community(creator_id, body.name)
    return BaseSuccessResponse(data=result)


# ======================================================================
# List — Active / Inactive
# ======================================================================

@router.get(
    "/active",
    response_model=BaseSuccessResponse[CommunityListResponse],
    summary="List Active Communities",
    description=(
        "Returns a paginated list of the creator's active communities, "
        "ordered by creation date (newest first)."
    ),
)
async def list_active_communities(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    creator_id: uuid.UUID = Depends(get_current_creator),
    service: CommunityService = Depends(get_community_service),
) -> BaseSuccessResponse[CommunityListResponse]:
    """List active communities with pagination."""
    result = await service.list_active(creator_id, page, page_size)
    return BaseSuccessResponse(data=result)


@router.get(
    "/inactive",
    response_model=BaseSuccessResponse[CommunityListResponse],
    summary="List Inactive Communities",
    description=(
        "Returns a paginated list of the creator's inactive communities, "
        "ordered by creation date (newest first)."
    ),
)
async def list_inactive_communities(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    creator_id: uuid.UUID = Depends(get_current_creator),
    service: CommunityService = Depends(get_community_service),
) -> BaseSuccessResponse[CommunityListResponse]:
    """List inactive communities with pagination."""
    result = await service.list_inactive(creator_id, page, page_size)
    return BaseSuccessResponse(data=result)


# ======================================================================
# Read — Single
# ======================================================================

@router.get(
    "/{community_id}",
    response_model=BaseSuccessResponse[CommunityResponse],
    summary="Get Community",
    description="Returns details of a single community owned by the creator.",
)
async def get_community(
    community_id: uuid.UUID,
    creator_id: uuid.UUID = Depends(get_current_creator),
    service: CommunityService = Depends(get_community_service),
) -> BaseSuccessResponse[CommunityResponse]:
    """Get a single community by ID."""
    result = await service.get_community(community_id, creator_id)
    return BaseSuccessResponse(data=result)


# ======================================================================
# Update
# ======================================================================

@router.patch(
    "/{community_id}",
    response_model=BaseSuccessResponse[CommunityResponse],
    summary="Update Community",
    description=(
        "Updates the community name. Name must be unique per creator "
        "(3–100 characters). Telegram fields cannot be modified here."
    ),
)
async def update_community(
    community_id: uuid.UUID,
    body: UpdateCommunityRequest,
    creator_id: uuid.UUID = Depends(get_current_creator),
    service: CommunityService = Depends(get_community_service),
) -> BaseSuccessResponse[CommunityResponse]:
    """Update a community's name."""
    result = await service.update_community(community_id, creator_id, body.name)
    return BaseSuccessResponse(data=result)


# ======================================================================
# Activate / Deactivate
# ======================================================================

@router.patch(
    "/{community_id}/activate",
    response_model=BaseSuccessResponse[CommunityResponse],
    summary="Activate Community",
    description="Sets the community to active state.",
)
async def activate_community(
    community_id: uuid.UUID,
    creator_id: uuid.UUID = Depends(get_current_creator),
    service: CommunityService = Depends(get_community_service),
) -> BaseSuccessResponse[CommunityResponse]:
    """Activate a community."""
    result = await service.activate_community(community_id, creator_id)
    return BaseSuccessResponse(data=result)


@router.patch(
    "/{community_id}/deactivate",
    response_model=BaseSuccessResponse[CommunityResponse],
    summary="Deactivate Community",
    description=(
        "Sets the community to inactive state. Telegram connection "
        "remains untouched — only PulseAccess business operations are disabled."
    ),
)
async def deactivate_community(
    community_id: uuid.UUID,
    creator_id: uuid.UUID = Depends(get_current_creator),
    service: CommunityService = Depends(get_community_service),
) -> BaseSuccessResponse[CommunityResponse]:
    """Deactivate a community."""
    result = await service.deactivate_community(community_id, creator_id)
    return BaseSuccessResponse(data=result)
