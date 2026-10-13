"""Payment router exposing order creation and checkout endpoints."""

import uuid
from fastapi import APIRouter, Depends, status

from app.core.config import Settings, get_settings
from app.modules.auth.schemas import BaseSuccessResponse
from app.modules.payment.dependencies import get_payment_service
from app.modules.payment.schemas import (
    CreatePaymentOrderRequest,
    PaymentOrderResponse,
)
from app.modules.payment.services import PaymentService

router = APIRouter(tags=["payments"])


@router.post(
    "/api/v1/payments/orders",
    response_model=BaseSuccessResponse[PaymentOrderResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Razorpay payment order",
)
async def create_payment_order(
    request: CreatePaymentOrderRequest,
    service: PaymentService = Depends(get_payment_service),
    settings: Settings = Depends(get_settings),
) -> BaseSuccessResponse[PaymentOrderResponse]:
    """Generate a payment order for checkout."""
    order = await service.create_order(
        member_id=request.member_id,
        plan_id=request.plan_id,
    )
    response_data = PaymentOrderResponse.model_validate(order)
    response_data.key_id = settings.RAZORPAY_KEY_ID
    return BaseSuccessResponse(data=response_data)


@router.get(
    "/api/v1/payments/orders/{order_id}",
    response_model=BaseSuccessResponse[PaymentOrderResponse],
    summary="Get payment order by ID",
)
async def get_payment_order(
    order_id: uuid.UUID,
    service: PaymentService = Depends(get_payment_service),
    settings: Settings = Depends(get_settings),
) -> BaseSuccessResponse[PaymentOrderResponse]:
    """Retrieve details of a payment order."""
    order = await service.get_order(order_id)
    response_data = PaymentOrderResponse.model_validate(order)
    response_data.key_id = settings.RAZORPAY_KEY_ID
    return BaseSuccessResponse(data=response_data)


# Webhook endpoint stub (to be completed in Step 5)
@router.post("/api/v1/webhooks/razorpay", tags=["webhooks"])
async def razorpay_webhook():
    return {"status": "received"}
