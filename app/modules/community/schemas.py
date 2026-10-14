"""Community module Pydantic v2 schemas.

Request/response DTOs for all Community API endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ======================================================================
# Request Schemas
# ======================================================================

def _strip(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


def _blank_to_none(value: object) -> object:
    value = _strip(value)
    return value or None


class CreateCommunityRequest(BaseModel):
    """Payload for creating a new community."""

    name: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Community name (3–100 characters).",
    )
    description: str | None = Field(
        None,
        max_length=500,
        description="Optional community description (up to 500 characters).",
    )

    _strip_name = field_validator("name", mode="before")(_strip)
    _clean_description = field_validator("description", mode="before")(_blank_to_none)


class UpdateCommunityRequest(BaseModel):
    """Payload for updating a community.

    Omitting `description` leaves it unchanged; sending null or "" clears it.
    """

    name: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="New community name (3–100 characters).",
    )
    description: str | None = Field(
        None,
        max_length=500,
        description="New description (up to 500 characters); null clears it.",
    )

    _strip_name = field_validator("name", mode="before")(_strip)
    _clean_description = field_validator("description", mode="before")(_blank_to_none)


# ======================================================================
# Response Schemas
# ======================================================================

class CommunityResponse(BaseModel):
    """Public representation of a Community."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
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
