# Payment & Subscription Modules

## Overview

Full implementation of Razorpay-backed payment processing and subscription lifecycle management for the PulseAccess platform.

---

## Modules

### Payment Module (`app/modules/payment/`)

#### Features
- **Order Creation** — Creates a Razorpay order for a given `member_id` + `plan_id`. Converts plan price (INR) to paise, generates a receipt ID, and persists the order locally.
- **Webhook Handler** — `POST /api/v1/webhooks/razorpay` handles `payment.captured` and `order.paid` events.
  - HMAC-SHA256 signature verification (constant-time comparison) against `RAZORPAY_WEBHOOK_SECRET`
  - Idempotency via `PaymentEvent.event_id` unique constraint — duplicate replays are detected and skipped
  - On successful capture: marks order as `PAID` and triggers subscription activation
- **Order Retrieval** — `GET /api/v1/payments/orders/{order_id}` returns order status

#### API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/payments/orders` | Create a Razorpay payment order |
| `GET` | `/api/v1/payments/orders/{order_id}` | Fetch order by ID |
| `POST` | `/api/v1/webhooks/razorpay` | Razorpay webhook receiver |

#### Models
- `PaymentOrder` — stores Razorpay order ID, member, plan, amount in paise, status, receipt
- `PaymentEvent` — audit log for every webhook event with idempotency key

---

### Subscription Module (`app/modules/subscription/`)

#### Features
- **Activate or Renew** — Creates a new subscription or extends an existing one from `max(ends_at, now)` to handle overlapping renewals correctly
- **Extend** — Manually extend a subscription's `ends_at` by N days
- **Cancel** — Sets status to `CANCELLED` and records `cancelled_at`
- **List** — Fetch all subscriptions for a member with active status filtering

#### API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/subscriptions` | Create / activate a subscription |
| `GET` | `/api/v1/subscriptions/{id}` | Fetch subscription by ID |
| `POST` | `/api/v1/subscriptions/{id}/extend` | Extend subscription duration |
| `POST` | `/api/v1/subscriptions/{id}/cancel` | Cancel a subscription |
| `GET` | `/api/v1/subscriptions/member/{member_id}` | List all member subscriptions |

#### Statuses
`ACTIVE` → `EXPIRED` / `CANCELLED` / `PENDING`

---

### Razorpay Infrastructure (`app/infrastructure/razorpay/`)

- `RazorpayDriver` — async `httpx` client wrapping the Razorpay v1 API
  - `create_order(amount_paise, currency, receipt)` — creates order via Razorpay API
  - `verify_webhook_signature(payload_bytes, signature)` — HMAC-SHA256 constant-time verification
  - `fetch_payment(payment_id)` — retrieves payment details
- `RazorpayClient` — protocol/interface definition for dependency injection
- `RazorpayAPIError` — typed exception with `status_code` and `message`

---

## Changes Made (This Session)

### Fix: Hardcoded 30-Day Subscription Duration

**Problem:** `payment/services.py` hardcoded `duration_days=30` when activating a subscription on webhook capture, ignoring any per-plan duration.

**Fix:**
1. Added `duration_days: Mapped[int]` (default `30`) to `Plan` model
2. Updated `CreatePlanRequest`, `UpdatePlanRequest`, `PlanResponse` schemas to include `duration_days`
3. Webhook handler now fetches the plan via `get_plan_by_id(order.plan_id)` and reads `plan.duration_days` (falls back to `30` if plan not found)
4. Added Alembic migration `e3c7f1a09b21` — `ALTER TABLE plans ADD COLUMN duration_days INTEGER NOT NULL DEFAULT 30`

**Files changed:**
- `app/modules/plan/models.py`
- `app/modules/plan/schemas.py`
- `app/modules/payment/services.py`
- `alembic/versions/e3c7f1a09b21_add_duration_days_to_plans.py`

---

## Database Schema

```
plans
├── id (UUID, PK)
├── community_id (UUID)
├── name (String)
├── price (Float)
└── duration_days (Integer, default=30)   ← added

payment_orders
├── id (UUID, PK)
├── razorpay_order_id (String, unique)
├── member_id (UUID)
├── plan_id (UUID)
├── amount_paise (Integer)
├── currency (String, default='INR')
├── status (String)
├── receipt_id (String, nullable)
├── created_at (DateTime)
└── updated_at (DateTime, nullable)

payment_events
├── id (UUID, PK)
├── event_id (String, unique)            ← idempotency key
├── event_type (String)
├── payload (Text)
├── status (String)
└── created_at (DateTime)

subscriptions
├── id (UUID, PK)
├── member_id (UUID)
├── plan_id (UUID)
├── status (String)
├── starts_at (DateTime)
├── ends_at (DateTime)
├── cancelled_at (DateTime, nullable)
├── created_at (DateTime)
└── updated_at (DateTime, nullable)
```

---

## Test Results

### Unit Tests — 18/18 Passed

```
tests/test_payment_order.py::test_payment_repository_flow              PASSED
tests/test_payment_order.py::test_payment_service_create_order         PASSED
tests/test_payment_order.py::test_payment_service_nonexistent_plan_raises PASSED
tests/test_payment_order.py::test_payment_order_api_flow               PASSED

tests/test_payment_webhook.py::test_webhook_payment_captured_success   PASSED
tests/test_payment_webhook.py::test_webhook_invalid_signature_rejected PASSED
tests/test_payment_webhook.py::test_webhook_idempotency_duplicate_replay PASSED

tests/test_razorpay_driver.py::test_verify_webhook_signature_valid     PASSED
tests/test_razorpay_driver.py::test_verify_webhook_signature_tampered_payload PASSED
tests/test_razorpay_driver.py::test_verify_webhook_signature_invalid_sig PASSED
tests/test_razorpay_driver.py::test_verify_webhook_signature_missing_secret PASSED
tests/test_razorpay_driver.py::test_create_order_success               PASSED
tests/test_razorpay_driver.py::test_create_order_failure               PASSED
tests/test_razorpay_driver.py::test_fetch_payment_success              PASSED

tests/test_subscription.py::test_activate_and_renew_subscription       PASSED
tests/test_subscription.py::test_cancel_subscription                   PASSED
tests/test_subscription.py::test_get_nonexistent_subscription_raises   PASSED
tests/test_subscription.py::test_subscription_api_flow                 PASSED

18 passed in 0.45s
```

### Live Razorpay API (Test Mode)

Credentials: `rzp_test_TnHvLueLv364rt` (test mode, verified working)

| Test | Result |
|------|--------|
| `POST /v1/orders` — create order 499 INR | `order_TnJZRrIEQLKhSl` · `status=created` |
| `GET /v1/orders/{id}` — fetch order back | `status=created` · `amount_due=49900` |
| `RazorpayDriver.create_order` — 199 INR | `order_TnJa9ba2fQ37iX` · `status=created` |
| `verify_webhook_signature` — valid HMAC | `True` |
| `verify_webhook_signature` — bad signature | `False` |
| `fetch_payment` — nonexistent ID | `RazorpayAPIError(status=400)` raised correctly |

---

## Alembic Migrations

| Revision | Description |
|----------|-------------|
| `b4e91c8a1234` | Create `payment_orders`, `payment_events`; add columns to `subscriptions` |
| `e3c7f1a09b21` | Add `duration_days` column to `plans` (default 30) |

To apply:
```bash
alembic upgrade head
```
