"""Payment router exposing order creation and webhook processing endpoints."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, Request, status

from app.core.config import Settings, get_settings
from app.modules.auth.schemas import BaseSuccessResponse
from app.modules.payment.dependencies import get_payment_service
from app.modules.payment.schemas import (
    CreatePaymentOrderRequest,
    PaymentOrderResponse,
)
from app.modules.payment.services import PaymentService
from app.modules.telegram_connect.dependencies import require_member_telegram

router = APIRouter(tags=["payments"])


@router.post(
    "/api/v1/payments/orders",
    response_model=BaseSuccessResponse[PaymentOrderResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Razorpay payment order",
    description=(
        "Starts checkout for a plan. Requires a member login, and the member "
        "must have connected Telegram first."
    ),
)
async def create_payment_order(
    request: CreatePaymentOrderRequest,
    member_id: uuid.UUID = Depends(require_member_telegram),
    service: PaymentService = Depends(get_payment_service),
    settings: Settings = Depends(get_settings),
) -> BaseSuccessResponse[PaymentOrderResponse]:
    """Generate a payment order for checkout."""
    order = await service.create_order(
        member_id=member_id,
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


@router.post(
    "/api/v1/webhooks/razorpay",
    response_model=BaseSuccessResponse[dict[str, Any]],
    summary="Process Razorpay webhook event",
    tags=["webhooks"],
)
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(None, alias="X-Razorpay-Signature"),
    service: PaymentService = Depends(get_payment_service),
) -> BaseSuccessResponse[dict[str, Any]]:
    """Verify cryptographic signature and process incoming Razorpay webhook event."""
    raw_body = await request.body()
    result = await service.process_webhook(
        raw_payload_bytes=raw_body,
        signature=x_razorpay_signature,
    )
    return BaseSuccessResponse(data=result)
