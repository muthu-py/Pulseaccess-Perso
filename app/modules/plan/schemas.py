"""Plan module Pydantic v2 schemas.

Creators enter prices in rupees (up to 2 decimals); they are stored in paise.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, computed_field, field_validator

# Razorpay's minimum charge is ₹1
_MIN_PRICE = Decimal("1")
_MAX_PRICE = Decimal("500000")


def _strip(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


def _blank_to_none(value: object) -> object:
    value = _strip(value)
    return value or None


class CreatePlanRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Plan name, e.g. 'Monthly'.")
    description: str | None = Field(None, max_length=500)
    price: Decimal = Field(
        ...,
        ge=_MIN_PRICE,
        le=_MAX_PRICE,
        decimal_places=2,
        description="Price in rupees, e.g. 499 or 499.50.",
    )
    duration_days: int = Field(30, ge=1, le=3650, description="Access length per payment.")

    _strip_name = field_validator("name", mode="before")(_strip)
    _clean_description = field_validator("description", mode="before")(_blank_to_none)


class UpdatePlanRequest(BaseModel):
    """Partial update; omitted fields stay unchanged. Affects future payments only."""

    name: str | None = Field(None, min_length=2, max_length=100)
    description: str | None = Field(None, max_length=500)
    price: Decimal | None = Field(None, ge=_MIN_PRICE, le=_MAX_PRICE, decimal_places=2)
    duration_days: int | None = Field(None, ge=1, le=3650)

    _strip_name = field_validator("name", mode="before")(_strip)
    _clean_description = field_validator("description", mode="before")(_blank_to_none)


class PlanResponse(BaseModel):
    id: uuid.UUID
    community_id: uuid.UUID
    name: str
    description: str | None = None
    price_paise: int
    currency: str
    duration_days: int
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def price(self) -> str:
        """Price in rupees for display, e.g. "499.00"."""
        return f"{Decimal(self.price_paise) / 100:.2f}"
