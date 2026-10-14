"""Payment links: one single-use Razorpay link per purchase → webhook → subscription.

Uses the real RazorpayDriver; only Razorpay's HTTP API is faked (MockTransport).
"""

import hashlib
import hmac
import itertools
import json
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.infrastructure.razorpay.razorpay_driver import RazorpayDriver
from app.main import app as fastapi_app
from app.modules.payment.dependencies import get_razorpay_client
from app.modules.payment.models import PaymentOrder
from app.modules.plan.models import Plan
from app.modules.subscription.models import Subscription
from tests.helpers import auth_headers, make_community, make_member

WEBHOOK_SECRET = "whsec_test_123"
_ids = itertools.count(1)


class FakeRazorpay:
    """Answers POST /payment_links like Razorpay test mode; records requests."""

    def __init__(self) -> None:
        self.links: list[dict] = []
        self.fail = False

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"].startswith("Basic ")
        if request.method == "POST" and request.url.path.endswith("/payment_links"):
            if self.fail:
                return httpx.Response(400, json={"error": {"description": "bad request"}})
            body = json.loads(request.content)
            link_id = f"plink_{next(_ids):06d}"
            self.links.append(body)
            return httpx.Response(200, json={
                "id": link_id,
                "short_url": f"https://rzp.io/i/{link_id}",
                "status": "created",
                "amount": body["amount"],
                "currency": body["currency"],
                "reference_id": body["reference_id"],
            })
        raise AssertionError(f"unexpected Razorpay call {request.method} {request.url}")


@pytest.fixture
def razorpay() -> FakeRazorpay:
    return FakeRazorpay()


@pytest.fixture(autouse=True)
def _driver(async_client: AsyncClient, razorpay: FakeRazorpay):
    settings = get_settings().model_copy(update={
        "RAZORPAY_KEY_ID": "rzp_test_key",
        "RAZORPAY_KEY_SECRET": "rzp_test_secret",
        "RAZORPAY_WEBHOOK_SECRET": WEBHOOK_SECRET,
    })
    driver = RazorpayDriver(settings, transport=httpx.MockTransport(razorpay.handle))
    fastapi_app.dependency_overrides[get_razorpay_client] = lambda: driver


@pytest.fixture
async def setup(db_session: AsyncSession):
    """A connected community with a ₹499 / 30-day plan, and a member with Telegram."""
    community = await make_community(db_session, uuid.uuid4())
    plan = Plan(community_id=community.id, name="Monthly", price_paise=49900, duration_days=30)
    db_session.add(plan)
    member = await make_member(db_session)
    await db_session.flush()
    return {"community": community, "plan": plan, "member": member,
            "headers": auth_headers(member.id, "member")}


async def _buy(client: AsyncClient, plan_id, headers: dict):
    return await client.post(f"/api/v1/plans/{plan_id}/payment-link", headers=headers)


def _paid_event(link_id: str, amount: int, *, currency: str = "INR", payment_id: str | None = None) -> dict:
    payment_id = payment_id or f"pay_{uuid.uuid4().hex[:10]}"
    return {
        "event": "payment_link.paid",
        "payload": {
            "payment_link": {"entity": {
                "id": link_id, "amount": amount, "amount_paid": amount,
                "currency": currency, "status": "paid",
            }},
            "payment": {"entity": {
                "id": payment_id, "amount": amount, "currency": currency, "status": "captured",
            }},
        },
    }


async def _webhook(client: AsyncClient, event: dict, *, event_id: str | None = None):
    raw = json.dumps(event).encode()
    headers = {
        "Content-Type": "application/json",
        "X-Razorpay-Signature": hmac.new(WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest(),
        "X-Razorpay-Event-Id": event_id or f"evt_{uuid.uuid4().hex[:12]}",
    }
    resp = await client.post("/api/v1/webhooks/razorpay", content=raw, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _subscription(db: AsyncSession, member_id, plan_id) -> Subscription | None:
    result = await db.execute(select(Subscription).where(
        Subscription.member_id == member_id, Subscription.plan_id == plan_id,
    ))
    return result.scalar_one_or_none()


# ── creating links ──────────────────────────────────────────────────────


async def test_member_gets_a_single_use_payment_link(async_client: AsyncClient, setup, razorpay):
    resp = await _buy(async_client, setup["plan"].id, setup["headers"])

    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert data["payment_link_url"].startswith("https://rzp.io/i/plink_")
    assert data["amount_paise"] == 49900
    assert data["status"] == "created"

    sent = razorpay.links[-1]
    assert sent["amount"] == 49900
    assert sent["currency"] == "INR"
    assert sent["reference_id"] == data["id"]
    assert sent["accept_partial"] is False
    assert sent["notify"] == {"sms": False, "email": False}
    assert sent["customer"]["contact"] == setup["member"].phone
    assert sent["notes"]["plan_id"] == str(setup["plan"].id)
    expires = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
    assert sent["expire_by"] == int(expires.timestamp())
    assert expires - datetime.now(timezone.utc) > timedelta(minutes=15)


async def test_open_link_is_reused(async_client: AsyncClient, setup, razorpay):
    first = (await _buy(async_client, setup["plan"].id, setup["headers"])).json()["data"]
    second = (await _buy(async_client, setup["plan"].id, setup["headers"])).json()["data"]

    assert second["id"] == first["id"]
    assert len(razorpay.links) == 1


async def test_price_change_gets_a_new_link(
    async_client: AsyncClient, db_session: AsyncSession, setup, razorpay
):
    first = (await _buy(async_client, setup["plan"].id, setup["headers"])).json()["data"]
    setup["plan"].price_paise = 59900
    await db_session.flush()

    second = (await _buy(async_client, setup["plan"].id, setup["headers"])).json()["data"]
    assert second["id"] != first["id"]
    assert second["amount_paise"] == 59900


async def test_each_member_gets_their_own_link(
    async_client: AsyncClient, db_session: AsyncSession, setup
):
    other = auth_headers((await make_member(db_session)).id, "member")
    mine = (await _buy(async_client, setup["plan"].id, setup["headers"])).json()["data"]
    theirs = (await _buy(async_client, setup["plan"].id, other)).json()["data"]
    assert mine["payment_link_url"] != theirs["payment_link_url"]


async def test_unavailable_plans_are_refused(
    async_client: AsyncClient, db_session: AsyncSession, setup
):
    assert (await _buy(async_client, uuid.uuid4(), setup["headers"])).status_code == 404

    setup["plan"].is_active = False
    await db_session.flush()
    resp = await _buy(async_client, setup["plan"].id, setup["headers"])
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "PLAN_UNAVAILABLE"

    setup["plan"].is_active = True
    setup["community"].telegram_connection_status = "NEEDS_ATTENTION"
    await db_session.flush()
    assert (await _buy(async_client, setup["plan"].id, setup["headers"])).status_code == 409


async def test_member_without_telegram_is_blocked(
    async_client: AsyncClient, db_session: AsyncSession, setup
):
    member = await make_member(db_session, telegram=False)
    resp = await _buy(async_client, setup["plan"].id, auth_headers(member.id, "member"))
    assert resp.status_code == 403


async def test_razorpay_error_stores_nothing(
    async_client: AsyncClient, db_session: AsyncSession, setup, razorpay
):
    razorpay.fail = True
    resp = await _buy(async_client, setup["plan"].id, setup["headers"])
    assert resp.status_code == 502

    rows = (await db_session.execute(select(PaymentOrder))).scalars().all()
    assert rows == []


# ── webhook → subscription ──────────────────────────────────────────────


async def test_paid_link_activates_subscription(
    async_client: AsyncClient, db_session: AsyncSession, setup, razorpay
):
    payment = (await _buy(async_client, setup["plan"].id, setup["headers"])).json()["data"]
    link_id = payment["payment_link_url"].rsplit("/", 1)[1]

    result = await _webhook(async_client, _paid_event(link_id, 49900, payment_id="pay_abc"))
    assert result["status"] == "success"

    resp = await async_client.get(f"/api/v1/payments/{payment['id']}", headers=setup["headers"])
    data = resp.json()["data"]
    assert data["status"] == "paid"
    assert data["paid_at"] is not None

    sub = await _subscription(db_session, setup["member"].id, setup["plan"].id)
    assert sub is not None and sub.status == "active"
    assert abs((sub.ends_at - sub.starts_at) - timedelta(days=30)) < timedelta(seconds=5)


async def test_paying_again_extends_the_subscription(
    async_client: AsyncClient, db_session: AsyncSession, setup
):
    first = (await _buy(async_client, setup["plan"].id, setup["headers"])).json()["data"]
    await _webhook(async_client, _paid_event(first["payment_link_url"].rsplit("/", 1)[1], 49900))
    sub = await _subscription(db_session, setup["member"].id, setup["plan"].id)
    first_end = sub.ends_at

    # Paid link is closed, so buying again creates a new one
    second = (await _buy(async_client, setup["plan"].id, setup["headers"])).json()["data"]
    assert second["id"] != first["id"]
    await _webhook(async_client, _paid_event(second["payment_link_url"].rsplit("/", 1)[1], 49900))

    await db_session.refresh(sub)
    assert abs((sub.ends_at - first_end) - timedelta(days=30)) < timedelta(seconds=5)


async def test_wrong_amount_does_not_activate(
    async_client: AsyncClient, db_session: AsyncSession, setup
):
    payment = (await _buy(async_client, setup["plan"].id, setup["headers"])).json()["data"]
    link_id = payment["payment_link_url"].rsplit("/", 1)[1]

    result = await _webhook(async_client, _paid_event(link_id, 100))
    assert result["status"] == "rejected"

    assert await _subscription(db_session, setup["member"].id, setup["plan"].id) is None
    resp = await async_client.get(f"/api/v1/payments/{payment['id']}", headers=setup["headers"])
    assert resp.json()["data"]["status"] == "created"


async def test_duplicate_event_is_applied_once(
    async_client: AsyncClient, db_session: AsyncSession, setup
):
    payment = (await _buy(async_client, setup["plan"].id, setup["headers"])).json()["data"]
    event = _paid_event(payment["payment_link_url"].rsplit("/", 1)[1], 49900)

    await _webhook(async_client, event, event_id="evt_same")
    result = await _webhook(async_client, event, event_id="evt_same")
    assert result["status"] == "already_processed"

    sub = await _subscription(db_session, setup["member"].id, setup["plan"].id)
    assert abs((sub.ends_at - sub.starts_at) - timedelta(days=30)) < timedelta(seconds=5)


async def test_payment_captured_first_does_not_block_link_paid(
    async_client: AsyncClient, db_session: AsyncSession, setup
):
    """Razorpay also sends payment.captured for link payments, with the same payment id."""
    payment = (await _buy(async_client, setup["plan"].id, setup["headers"])).json()["data"]
    link_id = payment["payment_link_url"].rsplit("/", 1)[1]

    await _webhook(async_client, {
        "event": "payment.captured",
        "payload": {"payment": {"entity": {
            "id": "pay_shared", "order_id": "order_internal_x", "amount": 49900,
        }}},
    })
    await _webhook(async_client, _paid_event(link_id, 49900, payment_id="pay_shared"))

    assert await _subscription(db_session, setup["member"].id, setup["plan"].id) is not None


async def test_expired_link_event(async_client: AsyncClient, setup):
    payment = (await _buy(async_client, setup["plan"].id, setup["headers"])).json()["data"]
    link_id = payment["payment_link_url"].rsplit("/", 1)[1]

    await _webhook(async_client, {
        "event": "payment_link.expired",
        "payload": {"payment_link": {"entity": {"id": link_id, "status": "expired"}}},
    })

    resp = await async_client.get(f"/api/v1/payments/{payment['id']}", headers=setup["headers"])
    assert resp.json()["data"]["status"] == "expired"


async def test_link_past_expiry_reads_expired_and_is_replaced(
    async_client: AsyncClient, db_session: AsyncSession, setup
):
    payment = (await _buy(async_client, setup["plan"].id, setup["headers"])).json()["data"]
    await db_session.execute(
        update(PaymentOrder)
        .where(PaymentOrder.id == uuid.UUID(payment["id"]))
        .values(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
    )

    resp = await async_client.get(f"/api/v1/payments/{payment['id']}", headers=setup["headers"])
    assert resp.json()["data"]["status"] == "expired"

    fresh = (await _buy(async_client, setup["plan"].id, setup["headers"])).json()["data"]
    assert fresh["id"] != payment["id"]


async def test_members_cannot_see_each_others_payments(
    async_client: AsyncClient, db_session: AsyncSession, setup
):
    payment = (await _buy(async_client, setup["plan"].id, setup["headers"])).json()["data"]
    other = auth_headers((await make_member(db_session)).id, "member")

    resp = await async_client.get(f"/api/v1/payments/{payment['id']}", headers=other)
    assert resp.status_code == 404


async def test_bad_signature_rejected(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/v1/webhooks/razorpay",
        content=b'{"event": "payment_link.paid"}',
        headers={"Content-Type": "application/json", "X-Razorpay-Signature": "forged"},
    )
    assert resp.status_code == 400
