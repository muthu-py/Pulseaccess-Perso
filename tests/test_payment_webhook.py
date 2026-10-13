import hashlib
import hmac
import json
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.infrastructure.razorpay.razorpay_interface import RazorpayClient
from app.modules.payment.enums import PaymentOrderStatus
from app.modules.payment.models import PaymentEvent, PaymentOrder
from app.modules.plan.models import Plan
from app.modules.subscription.models import Subscription


class WebhookTestRazorpayClient(RazorpayClient):
    """Test client stub for verifying webhook processing without live Razorpay keys."""

    def __init__(self, webhook_secret: str = "test_webhook_secret_123") -> None:
        self.webhook_secret = webhook_secret

    async def create_order(self, amount_paise: int, currency: str = "INR", receipt=None, notes=None):
        return {"id": "order_mock", "status": "created"}

    def verify_webhook_signature(self, payload_bytes: bytes, signature: str) -> bool:
        if not signature:
            return False
        expected = hmac.new(
            key=self.webhook_secret.encode("utf-8"),
            msg=payload_bytes,
            digestmod=hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def fetch_payment(self, payment_id: str):
        return {"id": payment_id, "status": "captured"}


@pytest.fixture
def webhook_client_and_secret():
    secret = "test_webhook_secret_123"
    client = WebhookTestRazorpayClient(webhook_secret=secret)
    return client, secret


@pytest.mark.asyncio
async def test_webhook_payment_captured_success(
    async_client: AsyncClient,
    db_session: AsyncSession,
    webhook_client_and_secret,
):
    from app.main import app as fastapi_app
    from app.modules.payment.dependencies import get_razorpay_client

    test_client, secret = webhook_client_and_secret
    fastapi_app.dependency_overrides[get_razorpay_client] = lambda: test_client

    try:
        # 1. Setup Plan and Order in DB
        member_id = uuid.uuid4()
        plan_id = uuid.uuid4()
        rzp_order_id = "order_test_capture_001"

        plan = Plan(id=plan_id, community_id=uuid.uuid4(), name="Pro Plan", price=499.0)
        order = PaymentOrder(
            id=uuid.uuid4(),
            razorpay_order_id=rzp_order_id,
            member_id=member_id,
            plan_id=plan_id,
            amount_paise=49900,
            currency="INR",
            status=PaymentOrderStatus.CREATED.value,
        )
        db_session.add_all([plan, order])
        await db_session.commit()

        # 2. Build Webhook Payload
        payload_data = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test_001",
                        "order_id": rzp_order_id,
                        "amount": 49900,
                        "status": "captured",
                    }
                }
            },
        }
        raw_body = json.dumps(payload_data).encode("utf-8")
        signature = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

        # 3. Post to Webhook
        res = await async_client.post(
            "/api/v1/webhooks/razorpay",
            content=raw_body,
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": signature,
            },
        )
        assert res.status_code == 200
        assert res.json()["data"]["status"] == "success"

        # 4. Verify PaymentOrder transitioned to PAID
        await db_session.refresh(order)
        assert order.status == PaymentOrderStatus.PAID.value

        # 5. Verify Subscription was created and is ACTIVE
        stmt = select(Subscription).where(
            Subscription.member_id == member_id,
            Subscription.plan_id == plan_id,
        )
        sub_result = await db_session.execute(stmt)
        sub = sub_result.scalar_one_or_none()
        assert sub is not None
        assert sub.status == "active"
        assert sub.ends_at > sub.starts_at

        # 6. Verify PaymentEvent logged in DB
        stmt_evt = select(PaymentEvent).where(PaymentEvent.event_id == "pay_test_001")
        evt_result = await db_session.execute(stmt_evt)
        evt = evt_result.scalar_one_or_none()
        assert evt is not None
        assert evt.status == "processed"

    finally:
        fastapi_app.dependency_overrides.pop(get_razorpay_client, None)


@pytest.mark.asyncio
async def test_webhook_invalid_signature_rejected(
    async_client: AsyncClient,
    webhook_client_and_secret,
):
    from app.main import app as fastapi_app
    from app.modules.payment.dependencies import get_razorpay_client

    test_client, _ = webhook_client_and_secret
    fastapi_app.dependency_overrides[get_razorpay_client] = lambda: test_client

    try:
        raw_body = b'{"event": "payment.captured"}'
        res = await async_client.post(
            "/api/v1/webhooks/razorpay",
            content=raw_body,
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": "forged_tampered_signature",
            },
        )
        assert res.status_code == 400
        assert "Invalid webhook signature" in res.text
    finally:
        fastapi_app.dependency_overrides.pop(get_razorpay_client, None)


@pytest.mark.asyncio
async def test_webhook_idempotency_duplicate_replay(
    async_client: AsyncClient,
    db_session: AsyncSession,
    webhook_client_and_secret,
):
    from app.main import app as fastapi_app
    from app.modules.payment.dependencies import get_razorpay_client

    test_client, secret = webhook_client_and_secret
    fastapi_app.dependency_overrides[get_razorpay_client] = lambda: test_client

    try:
        member_id = uuid.uuid4()
        plan_id = uuid.uuid4()
        rzp_order_id = "order_test_replay_002"

        plan = Plan(id=plan_id, community_id=uuid.uuid4(), name="VIP Plan", price=999.0)
        order = PaymentOrder(
            id=uuid.uuid4(),
            razorpay_order_id=rzp_order_id,
            member_id=member_id,
            plan_id=plan_id,
            amount_paise=99900,
            currency="INR",
            status=PaymentOrderStatus.CREATED.value,
        )
        db_session.add_all([plan, order])
        await db_session.commit()

        payload_data = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test_replay_002",
                        "order_id": rzp_order_id,
                        "amount": 99900,
                    }
                }
            },
        }
        raw_body = json.dumps(payload_data).encode("utf-8")
        signature = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

        # 1. First webhook call -> success
        res1 = await async_client.post(
            "/api/v1/webhooks/razorpay",
            content=raw_body,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": signature},
        )
        assert res1.status_code == 200
        assert res1.json()["data"]["status"] == "success"

        # 2. Second webhook call with same event_id -> already_processed
        res2 = await async_client.post(
            "/api/v1/webhooks/razorpay",
            content=raw_body,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": signature},
        )
        assert res2.status_code == 200
        assert res2.json()["data"]["status"] == "already_processed"

        # 3. Check that only 1 subscription exists for this member
        stmt = select(Subscription).where(Subscription.member_id == member_id)
        subs = (await db_session.execute(stmt)).scalars().all()
        assert len(subs) == 1
    finally:
        fastapi_app.dependency_overrides.pop(get_razorpay_client, None)
