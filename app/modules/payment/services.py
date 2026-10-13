"""Payment service orchestrating order creation and payment workflows."""

import json
import uuid
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.infrastructure.razorpay.razorpay_exceptions import RazorpayAPIError
from app.infrastructure.razorpay.razorpay_interface import RazorpayClient
from app.modules.payment.enums import PaymentEventStatus, PaymentOrderStatus
from app.modules.payment.exceptions import (
    InvalidWebhookSignatureError,
    PaymentOrderCreationError,
    PaymentOrderNotFoundError,
    PlanNotFoundError,
)
from app.modules.payment.models import PaymentOrder
from app.modules.payment.repositories import PaymentRepository
from app.modules.subscription.services import SubscriptionService

logger = get_logger(__name__)


class PaymentService:
    """Business logic for checkout order generation and webhook event processing."""

    def __init__(
        self,
        repository: PaymentRepository,
        razorpay_client: RazorpayClient,
        settings: Settings,
        subscription_service: SubscriptionService | None = None,
    ) -> None:
        self._repo = repository
        self._razorpay = razorpay_client
        self._settings = settings
        self._subscription_service = subscription_service

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

    async def process_webhook(
        self,
        raw_payload_bytes: bytes,
        signature: str | None,
    ) -> dict[str, Any]:
        """Process an incoming Razorpay webhook event with signature check and idempotency."""
        if not signature:
            logger.warning("Missing X-Razorpay-Signature in webhook request")
            raise InvalidWebhookSignatureError("Missing webhook signature")

        if not self._razorpay.verify_webhook_signature(raw_payload_bytes, signature):
            logger.warning("Invalid X-Razorpay-Signature in webhook request")
            raise InvalidWebhookSignatureError("Invalid webhook signature")

        try:
            payload = json.loads(raw_payload_bytes.decode("utf-8"))
        except Exception as exc:
            logger.error("Failed to parse webhook JSON payload: %s", exc)
            return {"status": "error", "message": "Invalid JSON payload"}

        event_name = payload.get("event", "unknown")
        event_payload = payload.get("payload", {})

        payment_entity = event_payload.get("payment", {}).get("entity", {})
        order_entity = event_payload.get("order", {}).get("entity", {})

        # Determine unique event identifier (payment id or razorpay event id)
        event_id = payment_entity.get("id") or payload.get("event_id") or order_entity.get("id")

        # Idempotency check: have we already processed this event?
        if event_id:
            existing_event = await self._repo.get_event_by_id(event_id)
            if existing_event is not None:
                logger.info("Webhook event %s already processed. Skipping.", event_id)
                return {"status": "already_processed", "event_id": event_id}

        # Process capture / payment success
        if event_name in ("payment.captured", "order.paid"):
            razorpay_order_id = payment_entity.get("order_id") or order_entity.get("id")
            if razorpay_order_id:
                order = await self._repo.get_order_by_razorpay_id(razorpay_order_id)
                if order:
                    await self._repo.update_order_status(order, PaymentOrderStatus.PAID)
                    if self._subscription_service:
                        plan = await self._repo.get_plan_by_id(order.plan_id)
                        duration_days = plan.duration_days if plan else 30
                        await self._subscription_service.activate_or_renew(
                            member_id=order.member_id,
                            plan_id=order.plan_id,
                            duration_days=duration_days,
                        )
                        logger.info(
                            "Activated subscription for member %s, plan %s",
                            order.member_id,
                            order.plan_id,
                        )

        # Record event in audit log
        await self._repo.record_event(
            event_id=event_id,
            event_type=event_name,
            payload=raw_payload_bytes.decode("utf-8"),
            status=PaymentEventStatus.PROCESSED,
        )

        return {"status": "success", "event": event_name}
