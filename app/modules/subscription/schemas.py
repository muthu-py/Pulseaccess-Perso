"""Subscription Pydantic schemas for request validation and response serialization."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SubscriptionResponse(BaseModel):
    """API response model for a single subscription."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    member_id: uuid.UUID
    plan_id: uuid.UUID
    status: str
    starts_at: datetime
    ends_at: datetime
    cancelled_at: datetime | None = None
    created_at: datetime


class CreateSubscriptionRequest(BaseModel):
    """Request payload to create or activate a subscription."""

    member_id: uuid.UUID
    plan_id: uuid.UUID
    duration_days: int = Field(default=30, gt=0)


class ExtendSubscriptionRequest(BaseModel):
    """Request payload to extend an active subscription."""

    days: int = Field(gt=0, description="Number of days to extend subscription")


class SubscriptionListResponse(BaseModel):
    """API response model for listing multiple subscriptions."""

    subscriptions: list[SubscriptionResponse]
    total: int
