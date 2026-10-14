"""Payment service: one Razorpay Payment Link per purchase, webhook → subscription.

Flow:
  1. A member picks a plan → create_payment_link() stores a purchase row and
     creates a single-use Razorpay Payment Link (reference_id = row id).
  2. The member pays on Razorpay's hosted page.
  3. Razorpay sends `payment_link.paid` → the amount is checked, the row is
     marked PAID and the subscription is activated or extended.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.infrastructure.razorpay.razorpay_exceptions import RazorpayAPIError
from app.infrastructure.razorpay.razorpay_interface import RazorpayClient
from app.modules.payment.enums import PaymentEventStatus, PaymentOrderStatus
from app.modules.payment.exceptions import (
    InvalidWebhookSignatureError,
    PaymentNotFoundError,
    PaymentOrderCreationError,
    PlanNotFoundError,
    PlanUnavailableError,
)
from app.modules.payment.models import PaymentOrder
from app.modules.payment.repositories import PaymentRepository
from app.modules.subscription.services import SubscriptionService
from app.modules.telegram.enums import TelegramConnectionStatus
from app.modules.telegram.services import TelegramService

logger = get_logger(__name__)

# Don't hand out a link that is about to expire; make a fresh one instead.
_REUSE_MIN_REMAINING = timedelta(minutes=5)


def _ensure_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class PaymentService:
    """Business logic for payment links and webhook event processing."""

    def __init__(
        self,
        repository: PaymentRepository,
        razorpay_client: RazorpayClient,
        settings: Settings,
        subscription_service: SubscriptionService | None = None,
        telegram_service: TelegramService | None = None,
    ) -> None:
        self._repo = repository
        self._razorpay = razorpay_client
        self._settings = settings
        self._subscription_service = subscription_service
        # Records the membership and DMs the member a "Join group" button.
        self._telegram_service = telegram_service

    # ══════════════════════════════════════════════════════════════════
    #  Member: buy a plan
    # ══════════════════════════════════════════════════════════════════

    async def create_payment_link(
        self,
        member_id: uuid.UUID,
        plan_id: uuid.UUID,
    ) -> PaymentOrder:
        """Return a payment link for this member and plan.

        An unpaid, unexpired link for the same plan and price is reused, so
        clicking "Buy" twice doesn't create two payable links.
        """
        plan = await self._repo.get_plan_by_id(plan_id)
        if plan is None:
            raise PlanNotFoundError()

        community = await self._repo.get_community(plan.community_id)
        if (
            not plan.is_active
            or community is None
            or not community.is_active
            or community.telegram_connection_status != TelegramConnectionStatus.CONNECTED.value
        ):
            raise PlanUnavailableError()

        now = datetime.now(timezone.utc)
        existing = await self._repo.get_open_link(member_id, plan_id, now + _REUSE_MIN_REMAINING)
        if existing is not None and existing.amount_paise == plan.price_paise:
            return existing

        member = await self._repo.get_member(member_id)
        if member is None:
            raise PaymentNotFoundError("Member not found.")

        expires_at = now + timedelta(minutes=self._settings.RAZORPAY_PAYMENT_LINK_EXPIRY_MINUTES)
        # The id doubles as Razorpay's reference_id; the row is stored only
        # once Razorpay has created the link, so failures leave nothing behind.
        payment_id = uuid.uuid4()

        try:
            link = await self._razorpay.create_payment_link(
                amount_paise=plan.price_paise,
                currency=plan.currency,
                reference_id=str(payment_id),
                description=f"{community.name} — {plan.name}"[:255],
                customer={"name": member.name, "email": member.email, "contact": member.phone},
                expire_by=int(expires_at.timestamp()),
                notes={
                    "payment_id": str(payment_id),
                    "member_id": str(member_id),
                    "plan_id": str(plan_id),
                    "community_id": str(community.id),
                },
                callback_url=self._settings.RAZORPAY_PAYMENT_CALLBACK_URL or None,
            )
        except RazorpayAPIError as exc:
            logger.error("Failed to create Razorpay payment link: %s", exc.message)
            raise PaymentOrderCreationError(detail="Could not create payment link") from exc

        order = await self._repo.add_order(
            PaymentOrder(
                id=payment_id,
                member_id=member_id,
                plan_id=plan_id,
                amount_paise=plan.price_paise,
                currency=plan.currency,
                status=PaymentOrderStatus.CREATED.value,
                expires_at=expires_at,
                razorpay_payment_link_id=link["id"],
                payment_link_url=link["short_url"],
            )
        )

        logger.info(
            "Payment link %s created for member %s, plan %s (%d paise)",
            link["id"], member_id, plan_id, plan.price_paise,
        )
        return order

    async def get_member_payment(
        self,
        member_id: uuid.UUID,
        payment_id: uuid.UUID,
    ) -> PaymentOrder:
        """A member's own payment; unpaid links past expiry read as expired."""
        order = await self._repo.get_order_by_id(payment_id)
        if order is None or order.member_id != member_id:
            raise PaymentNotFoundError()

        if (
            order.status == PaymentOrderStatus.CREATED.value
            and order.expires_at is not None
            and _ensure_utc(order.expires_at) <= datetime.now(timezone.utc)
        ):
            order.status = PaymentOrderStatus.EXPIRED.value
            await self._repo.save_order(order)
        return order

    # ══════════════════════════════════════════════════════════════════
    #  Razorpay webhook
    # ══════════════════════════════════════════════════════════════════

    async def process_webhook(
        self,
        raw_payload_bytes: bytes,
        signature: str | None,
        event_id_header: str | None = None,
    ) -> dict[str, Any]:
        """Verify, de-duplicate and apply a Razorpay webhook event."""
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
        link_entity = event_payload.get("payment_link", {}).get("entity", {})

        # Razorpay's X-Razorpay-Event-Id is unique per event. Without it, fall
        # back to the entity id (payment id for paid events).
        event_id = (
            event_id_header
            or payment_entity.get("id")
            or payload.get("event_id")
            or link_entity.get("id")
            or order_entity.get("id")
        )

        if event_id:
            existing_event = await self._repo.get_event_by_id(event_id)
            if existing_event is not None:
                logger.info("Webhook event %s already processed. Skipping.", event_id)
                return {"status": "already_processed", "event_id": event_id}

        if event_name == "payment_link.paid":
            outcome = await self._handle_link_paid(link_entity, payment_entity)
        elif event_name in ("payment_link.expired", "payment_link.cancelled"):
            outcome = await self._handle_link_closed(event_name, link_entity)
        elif event_name in ("payment.captured", "order.paid"):
            outcome = await self._handle_order_paid(payment_entity, order_entity)
        else:
            outcome = PaymentEventStatus.IGNORED

        await self._repo.record_event(
            event_id=event_id,
            event_type=event_name,
            payload=raw_payload_bytes.decode("utf-8"),
            status=outcome,
        )
        if outcome == PaymentEventStatus.FAILED:
            return {"status": "rejected", "event": event_name}
        return {"status": "success", "event": event_name}

    async def _handle_link_paid(
        self,
        link_entity: dict[str, Any],
        payment_entity: dict[str, Any],
    ) -> PaymentEventStatus:
        order = await self._repo.get_order_by_payment_link_id(link_entity.get("id", ""))
        if order is None:
            logger.warning("payment_link.paid for unknown link %s", link_entity.get("id"))
            return PaymentEventStatus.IGNORED
        return await self._mark_paid(
            order,
            amount=link_entity.get("amount_paid", payment_entity.get("amount")),
            currency=link_entity.get("currency", payment_entity.get("currency")),
            razorpay_payment_id=payment_entity.get("id"),
        )

    async def _handle_link_closed(
        self,
        event_name: str,
        link_entity: dict[str, Any],
    ) -> PaymentEventStatus:
        order = await self._repo.get_order_by_payment_link_id(link_entity.get("id", ""))
        if order is None or order.status != PaymentOrderStatus.CREATED.value:
            return PaymentEventStatus.IGNORED
        order.status = (
            PaymentOrderStatus.EXPIRED.value
            if event_name == "payment_link.expired"
            else PaymentOrderStatus.CANCELLED.value
        )
        await self._repo.save_order(order)
        return PaymentEventStatus.PROCESSED

    async def _handle_order_paid(
        self,
        payment_entity: dict[str, Any],
        order_entity: dict[str, Any],
    ) -> PaymentEventStatus:
        """payment.captured / order.paid.

        Payment-link payments also emit these (often without payment_link.paid
        if that event isn't subscribed). Razorpay copies our link notes onto
        the payment and order, and the order's receipt is our payment id, so
        they are matched to our row. Legacy Checkout orders match by order id.
        """
        order = await self._find_link_payment(payment_entity, order_entity)
        if order is not None:
            return await self._mark_paid(
                order,
                amount=order_entity.get("amount_paid", payment_entity.get("amount")),
                currency=order_entity.get("currency", payment_entity.get("currency")),
                razorpay_payment_id=payment_entity.get("id"),
            )

        razorpay_order_id = payment_entity.get("order_id") or order_entity.get("id")
        if not razorpay_order_id:
            return PaymentEventStatus.IGNORED
        order = await self._repo.get_order_by_razorpay_id(razorpay_order_id)
        if order is None or order.status == PaymentOrderStatus.PAID.value:
            return PaymentEventStatus.IGNORED

        await self._repo.update_order_status(order, PaymentOrderStatus.PAID)
        await self._activate_subscription(order)
        return PaymentEventStatus.PROCESSED

    async def _find_link_payment(
        self,
        payment_entity: dict[str, Any],
        order_entity: dict[str, Any],
    ) -> PaymentOrder | None:
        candidates = (
            (payment_entity.get("notes") or {}).get("payment_id"),
            (order_entity.get("notes") or {}).get("payment_id"),
            order_entity.get("receipt"),
        )
        for raw in candidates:
            try:
                payment_id = uuid.UUID(str(raw))
            except ValueError:
                continue
            order = await self._repo.get_order_by_id(payment_id)
            if order is not None and order.razorpay_payment_link_id is not None:
                return order
        return None

    async def _mark_paid(
        self,
        order: PaymentOrder,
        *,
        amount: Any,
        currency: Any,
        razorpay_payment_id: str | None,
    ) -> PaymentEventStatus:
        """Mark a payment-link purchase paid and activate its subscription, once."""
        if order.status == PaymentOrderStatus.PAID.value:
            return PaymentEventStatus.ALREADY_PROCESSED

        if amount != order.amount_paise or currency != order.currency:
            logger.error(
                "Payment %s amount mismatch: expected %s %s, got %s %s — not activating",
                order.id, order.amount_paise, order.currency, amount, currency,
            )
            return PaymentEventStatus.FAILED

        order.status = PaymentOrderStatus.PAID.value
        order.paid_at = datetime.now(timezone.utc)
        order.razorpay_payment_id = razorpay_payment_id
        await self._repo.save_order(order)
        await self._activate_subscription(order)
        return PaymentEventStatus.PROCESSED

    async def _activate_subscription(self, order: PaymentOrder) -> None:
        if self._subscription_service is None:
            return
        plan = await self._repo.get_plan_by_id(order.plan_id)
        duration_days = plan.duration_days if plan else 30
        await self._subscription_service.activate_or_renew(
            member_id=order.member_id,
            plan_id=order.plan_id,
            duration_days=duration_days,
        )
        logger.info(
            "Activated subscription for member %s, plan %s (%d days)",
            order.member_id, order.plan_id, duration_days,
        )
        if self._telegram_service is not None:
            await self._telegram_service.grant_access_after_payment(
                order.member_id, order.plan_id,
            )
