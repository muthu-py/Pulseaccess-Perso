"""Subscription router exposing CRUD and lifecycle endpoints."""

import uuid
from fastapi import APIRouter, Depends, status

from app.modules.auth.schemas import BaseSuccessResponse
from app.modules.subscription.dependencies import get_subscription_service
from app.modules.subscription.schemas import (
    CreateSubscriptionRequest,
    ExtendSubscriptionRequest,
    SubscriptionListResponse,
    SubscriptionResponse,
)
from app.modules.subscription.services import SubscriptionService

router = APIRouter(prefix="/api/v1/subscriptions", tags=["subscriptions"])


@router.post(
    "",
    response_model=BaseSuccessResponse[SubscriptionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create or activate subscription",
)
async def create_subscription(
    request: CreateSubscriptionRequest,
    service: SubscriptionService = Depends(get_subscription_service),
) -> BaseSuccessResponse[SubscriptionResponse]:
    """Create a new subscription or renew an existing one."""
    subscription = await service.activate_or_renew(
        member_id=request.member_id,
        plan_id=request.plan_id,
        duration_days=request.duration_days,
    )
    return BaseSuccessResponse(data=SubscriptionResponse.model_validate(subscription))


@router.get(
    "/{id}",
    response_model=BaseSuccessResponse[SubscriptionResponse],
    summary="Get subscription by ID",
)
async def get_subscription(
    id: uuid.UUID,
    service: SubscriptionService = Depends(get_subscription_service),
) -> BaseSuccessResponse[SubscriptionResponse]:
    """Fetch details of a single subscription."""
    subscription = await service.get_subscription(id)
    return BaseSuccessResponse(data=SubscriptionResponse.model_validate(subscription))


@router.post(
    "/{id}/extend",
    response_model=BaseSuccessResponse[SubscriptionResponse],
    summary="Extend subscription duration",
)
async def extend_subscription(
    id: uuid.UUID,
    request: ExtendSubscriptionRequest,
    service: SubscriptionService = Depends(get_subscription_service),
) -> BaseSuccessResponse[SubscriptionResponse]:
    """Extend the duration of an active subscription."""
    subscription = await service.extend_subscription(id, request.days)
    return BaseSuccessResponse(data=SubscriptionResponse.model_validate(subscription))


@router.post(
    "/{id}/cancel",
    response_model=BaseSuccessResponse[SubscriptionResponse],
    summary="Cancel a subscription",
)
async def cancel_subscription(
    id: uuid.UUID,
    service: SubscriptionService = Depends(get_subscription_service),
) -> BaseSuccessResponse[SubscriptionResponse]:
    """Cancel an active subscription."""
    subscription = await service.cancel_subscription(id)
    return BaseSuccessResponse(data=SubscriptionResponse.model_validate(subscription))


@router.get(
    "/member/{member_id}",
    response_model=BaseSuccessResponse[SubscriptionListResponse],
    summary="Get all subscriptions for a member",
)
async def get_member_subscriptions(
    member_id: uuid.UUID,
    service: SubscriptionService = Depends(get_subscription_service),
) -> BaseSuccessResponse[SubscriptionListResponse]:
    """List all historical and active subscriptions for a member."""
    subs = await service.get_member_subscriptions(member_id)
    items = [SubscriptionResponse.model_validate(s) for s in subs]
    return BaseSuccessResponse(
        data=SubscriptionListResponse(subscriptions=items, total=len(items))
    )
