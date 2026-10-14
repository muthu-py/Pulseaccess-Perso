import uuid
from typing import Any
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.infrastructure.security.jwt_service import JWTService
from app.infrastructure.razorpay.razorpay_interface import RazorpayClient
from app.modules.payment.enums import PaymentOrderStatus
from app.modules.payment.exceptions import PlanNotFoundError
from app.modules.payment.repositories import PaymentRepository
from app.modules.payment.services import PaymentService
from app.modules.member.models import Member
from app.modules.plan.models import Plan
from app.modules.telegram_connect.enums import OwnerType
from app.modules.telegram_connect.models import TelegramAccount


class MockRazorpayClient(RazorpayClient):
    """Mock RazorpayClient for testing order creation without calling external API."""

    def __init__(self) -> None:
        self.created_orders: list[dict[str, Any]] = []

    async def create_order(
        self,
        amount_paise: int,
        currency: str = "INR",
        receipt: str | None = None,
        notes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        order_data = {
            "id": f"order_mock_{uuid.uuid4().hex[:8]}",
            "amount": amount_paise,
            "currency": currency,
            "receipt": receipt,
            "notes": notes or {},
            "status": "created",
        }
        self.created_orders.append(order_data)
        return order_data

    def verify_webhook_signature(self, payload_bytes: bytes, signature: str) -> bool:
        return True

    async def fetch_payment(self, payment_id: str) -> dict[str, Any]:
        return {"id": payment_id, "status": "captured"}


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        DATABASE_URL="postgresql://user:pass@localhost:5432/db",
        JWT_SECRET_KEY="test_secret_key_at_least_32_characters_long",
        OTP_HASH_SECRET="test_otp_secret_at_least_32_characters_long",
        RAZORPAY_KEY_ID="rzp_test_mock_key",
        RAZORPAY_KEY_SECRET="mock_secret",
        RAZORPAY_WEBHOOK_SECRET="mock_webhook_secret",
    )


@pytest.mark.asyncio
async def test_payment_repository_flow(db_session: AsyncSession):
    repo = PaymentRepository(db_session)
    member_id = uuid.uuid4()
    plan_id = uuid.uuid4()
    rzp_id = f"order_{uuid.uuid4().hex[:8]}"

    # Create order
    order = await repo.create_order(
        razorpay_order_id=rzp_id,
        member_id=member_id,
        plan_id=plan_id,
        amount_paise=49900,
        currency="INR",
    )
    assert order.razorpay_order_id == rzp_id
    assert order.status == PaymentOrderStatus.CREATED.value
    assert order.amount_paise == 49900

    # Retrieve by razorpay_order_id
    fetched = await repo.get_order_by_razorpay_id(rzp_id)
    assert fetched is not None
    assert fetched.id == order.id

    # Update status
    updated = await repo.update_order_status(order, PaymentOrderStatus.PAID)
    assert updated.status == PaymentOrderStatus.PAID.value


@pytest.mark.asyncio
async def test_payment_service_create_order(
    db_session: AsyncSession, test_settings: Settings
):
    repo = PaymentRepository(db_session)
    mock_rzp = MockRazorpayClient()
    service = PaymentService(repo, mock_rzp, test_settings)

    # Insert a real Plan
    plan = Plan(
        id=uuid.uuid4(),
        community_id=uuid.uuid4(),
        name="Monthly Pro",
        price=499.0,
    )
    db_session.add(plan)
    await db_session.flush()

    member_id = uuid.uuid4()
    order = await service.create_order(member_id=member_id, plan_id=plan.id)

    assert order.member_id == member_id
    assert order.plan_id == plan.id
    assert order.amount_paise == 49900  # 499.0 * 100
    assert order.status == PaymentOrderStatus.CREATED.value
    assert len(mock_rzp.created_orders) == 1


@pytest.mark.asyncio
async def test_payment_service_nonexistent_plan_raises(
    db_session: AsyncSession, test_settings: Settings
):
    repo = PaymentRepository(db_session)
    mock_rzp = MockRazorpayClient()
    service = PaymentService(repo, mock_rzp, test_settings)

    with pytest.raises(PlanNotFoundError):
        await service.create_order(member_id=uuid.uuid4(), plan_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_payment_order_api_flow(
    async_client: AsyncClient, db_session: AsyncSession
):
    from app.main import app as fastapi_app
    from app.modules.payment.dependencies import get_razorpay_client

    mock_client = MockRazorpayClient()
    fastapi_app.dependency_overrides[get_razorpay_client] = lambda: mock_client

    try:
        # Create plan in DB
        plan = Plan(
            id=uuid.uuid4(),
            community_id=uuid.uuid4(),
            name="Quarterly Access",
            price=1299.0,
        )
        db_session.add(plan)
        await db_session.commit()

        # A logged-in member who has connected Telegram
        member_id = uuid.uuid4()
        db_session.add(Member(id=member_id, name="M", phone="+919999999999", email="m@example.com"))
        db_session.add(TelegramAccount(
            owner_type=OwnerType.MEMBER.value,
            owner_id=member_id,
            telegram_user_id="123",
            phone="+919999999999",
        ))
        await db_session.commit()
        token = JWTService(get_settings()).create_access_token(
            subject=str(member_id), extra_claims={"role": "member"},
        )

        # 1. Create order via API
        res = await async_client.post(
            "/api/v1/payments/orders",
            json={"plan_id": str(plan.id)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 201
        data = res.json()["data"]
        order_id = data["id"]
        assert data["amount_paise"] == 129900
        assert data["currency"] == "INR"
        assert data["status"] == "created"
        assert data["member_id"] == str(member_id)
        assert "razorpay_order_id" in data

        # 2. Fetch order via API
        res = await async_client.get(f"/api/v1/payments/orders/{order_id}")
        assert res.status_code == 200
        assert res.json()["data"]["id"] == order_id
    finally:
        fastapi_app.dependency_overrides.pop(get_razorpay_client, None)
