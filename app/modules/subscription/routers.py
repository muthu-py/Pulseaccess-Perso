"""Subscription router: members read their own subscriptions.

Subscriptions are created and extended only by a paid Razorpay webhook
(PaymentService), so there are no create / extend / cancel endpoints here.
"""

import uuid

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_member
from app.modules.auth.schemas import BaseSuccessResponse
from app.modules.subscription.dependencies import get_subscription_service
from app.modules.subscription.exceptions import SubscriptionNotFoundError
from app.modules.subscription.schemas import (
    SubscriptionListResponse,
    SubscriptionResponse,
)
from app.modules.subscription.services import SubscriptionService

router = APIRouter(prefix="/api/v1/subscriptions", tags=["subscriptions"])


@router.get(
    "/me",
    response_model=BaseSuccessResponse[SubscriptionListResponse],
    summary="My subscriptions",
)
async def get_my_subscriptions(
    member_id: uuid.UUID = Depends(get_current_member),
    service: SubscriptionService = Depends(get_subscription_service),
) -> BaseSuccessResponse[SubscriptionListResponse]:
    """All of the logged-in member's subscriptions, newest first."""
    subs = await service.get_member_subscriptions(member_id)
    items = [SubscriptionResponse.model_validate(s) for s in subs]
    return BaseSuccessResponse(
        data=SubscriptionListResponse(subscriptions=items, total=len(items))
    )


@router.get(
    "/{id}",
    response_model=BaseSuccessResponse[SubscriptionResponse],
    summary="Get one of my subscriptions",
)
async def get_subscription(
    id: uuid.UUID,
    member_id: uuid.UUID = Depends(get_current_member),
    service: SubscriptionService = Depends(get_subscription_service),
) -> BaseSuccessResponse[SubscriptionResponse]:
    """A single subscription, only if it belongs to the logged-in member."""
    subscription = await service.get_subscription(id)
    if subscription.member_id != member_id:
        raise SubscriptionNotFoundError()
    return BaseSuccessResponse(data=SubscriptionResponse.model_validate(subscription))
