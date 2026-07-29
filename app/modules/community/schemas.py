"""Community module Pydantic v2 schemas.

Request/response DTOs for all Community API endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ======================================================================
# Request Schemas
# ======================================================================

class CreateCommunityRequest(BaseModel):
    """Payload for creating a new community."""

    name: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Community name (3–100 characters).",
    )


class UpdateCommunityRequest(BaseModel):
    """Payload for updating a community."""

    name: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="New community name (3–100 characters).",
    )


# ======================================================================
# Response Schemas
# ======================================================================

class CommunityResponse(BaseModel):
    """Public representation of a Community."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    is_active: bool
    telegram_connected: bool
    created_at: datetime
    updated_at: datetime | None = None


class CommunityListResponse(BaseModel):
    """Paginated list of communities."""

    communities: list[CommunityResponse]
    page: int
    page_size: int
    total: int
