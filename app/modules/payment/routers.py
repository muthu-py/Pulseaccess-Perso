"""Payment router: member payment links and the Razorpay webhook."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, Request, status

from app.api.dependencies import get_current_member
from app.modules.auth.schemas import BaseSuccessResponse
from app.modules.payment.dependencies import get_payment_service
from app.modules.payment.schemas import PaymentLinkResponse
from app.modules.payment.services import PaymentService
from app.modules.telegram_connect.dependencies import require_member_telegram

router = APIRouter(tags=["payments"])


@router.post(
    "/api/v1/plans/{plan_id}/payment-link",
    response_model=BaseSuccessResponse[PaymentLinkResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Get a payment link for a plan",
    description=(
        "Creates a single-use Razorpay Payment Link for the logged-in member "
        "(who must have connected Telegram). Open `payment_link_url` to pay. "
        "An unpaid, unexpired link for the same plan is returned again "
        "instead of creating a second one."
    ),
)
async def create_payment_link(
    plan_id: uuid.UUID,
    member_id: uuid.UUID = Depends(require_member_telegram),
    service: PaymentService = Depends(get_payment_service),
) -> BaseSuccessResponse[PaymentLinkResponse]:
    order = await service.create_payment_link(member_id=member_id, plan_id=plan_id)
    return BaseSuccessResponse(data=PaymentLinkResponse.model_validate(order))


@router.get(
    "/api/v1/payments/{payment_id}",
    response_model=BaseSuccessResponse[PaymentLinkResponse],
    summary="Get my payment",
    description="Status of one of your payments: created, paid, expired or cancelled.",
)
async def get_payment(
    payment_id: uuid.UUID,
    member_id: uuid.UUID = Depends(get_current_member),
    service: PaymentService = Depends(get_payment_service),
) -> BaseSuccessResponse[PaymentLinkResponse]:
    order = await service.get_member_payment(member_id, payment_id)
    return BaseSuccessResponse(data=PaymentLinkResponse.model_validate(order))


@router.post(
    "/api/v1/webhooks/razorpay",
    response_model=BaseSuccessResponse[dict[str, Any]],
    summary="Process Razorpay webhook event",
    tags=["webhooks"],
)
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(None, alias="X-Razorpay-Signature"),
    x_razorpay_event_id: str | None = Header(None, alias="X-Razorpay-Event-Id"),
    service: PaymentService = Depends(get_payment_service),
) -> BaseSuccessResponse[dict[str, Any]]:
    """Verify cryptographic signature and process incoming Razorpay webhook event."""
    raw_body = await request.body()
    result = await service.process_webhook(
        raw_payload_bytes=raw_body,
        signature=x_razorpay_signature,
        event_id_header=x_razorpay_event_id,
    )
    return BaseSuccessResponse(data=result)
