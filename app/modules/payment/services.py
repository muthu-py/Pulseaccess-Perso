"""Payment service orchestrating order creation and payment workflows."""

import uuid
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.infrastructure.razorpay.razorpay_exceptions import RazorpayAPIError
from app.infrastructure.razorpay.razorpay_interface import RazorpayClient
from app.modules.payment.exceptions import (
    PaymentOrderCreationError,
    PaymentOrderNotFoundError,
    PlanNotFoundError,
)
from app.modules.payment.models import PaymentOrder
from app.modules.payment.repositories import PaymentRepository

logger = get_logger(__name__)


class PaymentService:
    """Business logic for checkout order generation and payment processing."""

    def __init__(
        self,
        repository: PaymentRepository,
        razorpay_client: RazorpayClient,
        settings: Settings,
    ) -> None:
        self._repo = repository
        self._razorpay = razorpay_client
        self._settings = settings

    async def create_order(
        self,
        member_id: uuid.UUID,
        plan_id: uuid.UUID,
    ) -> PaymentOrder:
        """Create a Razorpay payment order for a plan purchase."""
        plan = await self._repo.get_plan_by_id(plan_id)
        if plan is None:
            raise PlanNotFoundError()

        # Convert plan price (rupees) to paise (1 INR = 100 paise)
        amount_paise = int(round(plan.price * 100))
        receipt = f"rcpt_{uuid.uuid4().hex[:12]}"
        notes: dict[str, Any] = {
            "member_id": str(member_id),
            "plan_id": str(plan_id),
            "community_id": str(plan.community_id),
        }

        try:
            rzp_order = await self._razorpay.create_order(
                amount_paise=amount_paise,
                currency="INR",
                receipt=receipt,
                notes=notes,
            )
        except RazorpayAPIError as exc:
            logger.error("Failed to create Razorpay order: %s", exc.message)
            raise PaymentOrderCreationError(detail=exc.message) from exc

        razorpay_order_id = rzp_order["id"]

        order = await self._repo.create_order(
            razorpay_order_id=razorpay_order_id,
            member_id=member_id,
            plan_id=plan_id,
            amount_paise=amount_paise,
            currency="INR",
            receipt_id=receipt,
        )

        logger.info(
            "Created payment order %s (Razorpay ID: %s) for member %s, plan %s",
            order.id,
            razorpay_order_id,
            member_id,
            plan_id,
        )
        return order

    async def get_order(self, order_id: uuid.UUID) -> PaymentOrder:
        """Retrieve a payment order by ID."""
        order = await self._repo.get_order_by_id(order_id)
        if order is None:
            raise PaymentOrderNotFoundError()
        return order
