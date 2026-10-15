# PulseAccess — Feature Status

_Analysis of the workspace as of 2026-10-12 (branch `communities`)._

**Summary:** PulseAccess is a FastAPI modular monolith. Three areas are implemented: **Auth**, **Community management**, and **Telegram integration with background workers**. The business core is still scaffolding: **Plans, Subscriptions, Members, Payments, Dashboard and Notifications**. Nothing in the workspace has automated tests.

| Area | Status |
|------|--------|
| Core / config / logging / exceptions | Done |
| Auth (passwordless OTP + JWT) | Done |
| Community CRUD + lifecycle | Done |
| Telegram integration (6 workflows) | Mostly done (see gaps) |
| Background workers | Done, but they depend on unfinished modules |
| Plans | Stub |
| Subscriptions | Stub |
| Members | Stub |
| Payments (Razorpay) | Stub |
| Dashboard | Stub (hardcoded data) |
| Notifications | Stub |
| Tests | Not done |

---

## 1. Features Implemented

### 1.1 Core and infrastructure
- **Settings:** env-driven via pydantic-settings ([config.py](app/core/config.py)). `postgresql://` is rewritten to `postgresql+asyncpg://`.
- **Logging:** structured logging setup ([logging.py](app/core/logging.py)).
- **Global exception handlers and error types** ([exceptions.py](app/core/exceptions.py)).
- **HMAC-SHA256 hashing utilities** ([security.py](app/core/security.py)).
- **Async database layer:** SQLAlchemy 2.0 engine, session and Base.
- **Alembic migrations (4):** initial schema, auth tables, community fields, Telegram integration.
- **Email:** SMTP service (aiosmtplib) with an HTML OTP template ([smtp_email_service.py](app/infrastructure/email/smtp_email_service.py)).
- **Security services:** JWT issue/validate, HttpOnly refresh-cookie handling, session service.
- **Application lifespan:** starts and gracefully cancels the 4 workers; routers are registered in [main.py](app/main.py).

### 1.2 Auth module — `/api/v1/auth` (complete)
- `POST /register` — creator signup with email and username uniqueness checks.
- `POST /request-otp` — emails a 6-digit OTP. Always returns a generic success (anti-enumeration) and is rate-limited (5 per 15 min).
- `POST /verify-otp` — 5 max attempts and 5-min expiry. Returns an access token (15 min, JSON) and sets a refresh token (30 days, HttpOnly, SameSite=Lax).
- `POST /refresh` — refresh-token rotation (the old token is revoked).
- `POST /logout` — revokes the session and clears the cookie.
- OTPs and refresh tokens are stored only as HMAC hashes.
- `get_current_creator` dependency for protected routes ([dependencies.py](app/api/dependencies.py)).
- Models: `creators`, `login_otps`, `refresh_tokens`.

### 1.3 Community module — `/api/v1/communities` (complete)
- `POST /` — create a community (name unique per creator, 3–100 chars).
- `GET /active` and `GET /inactive` — paginated lists.
- `GET /{id}` — fetch one community.
- `PATCH /{id}` — rename.
- `PATCH /{id}/activate` and `/deactivate` — lifecycle toggles. Deactivating does not affect the Telegram connection.
- Ownership enforcement, custom exceptions, and a full router, service, repository, schema and model stack.

### 1.4 Telegram integration (phase 1)
**Creator endpoints** (JWT):
- `POST /api/v1/telegram/communities/{id}/connect` — generates a connection code and sets status to `CONNECTING`.
- `GET /api/v1/telegram/communities/{id}/status`
- `DELETE /api/v1/telegram/communities/{id}` — disconnect.

**Member endpoints:**
- `POST /api/v1/telegram/link` — deep link for account linking.
- `GET /api/v1/telegram/link/status`
- `POST /api/v1/telegram/communities/{id}/invite` — single-use, time-limited invite.

**Webhook:** `POST /api/v1/webhooks/telegram` verifies the secret header before parsing. It handles `message` (`/start` linking), `my_chat_member` (bot added, removed or promoted) and `chat_member` (join and leave logging).

**Other pieces:**
- Connection status lifecycle: `NOT_CONNECTED → CONNECTING → CONNECTED → NEEDS_ATTENTION / DISCONNECTED`.
- Persistent `telegram_operations` queue (`CREATE_INVITE`, `REMOVE_MEMBER`, `VERIFY_CONNECTION`, `SYNC_MEMBER`) with exponential backoff (1, 5, 15, 30 and 60 min). Permanent errors go straight to `FAILED`.
- Access revocation uses ban then unban, queued as `REMOVE_MEMBER`.
- `TelegramClient` protocol with two implementations: `TelegramDriver` (httpx, production) and `TelegramStub` (dev and test), plus an exception mapper and models.
- Agent guidance and skills in `.agents/`.

### 1.5 Background workers (started in lifespan)
| Worker | Interval | Purpose |
|--------|----------|---------|
| `telegram_retry_worker` | 60 s | Processes `PENDING` and `RETRYING` operations |
| `telegram_sync_worker` | 5 min | Verifies the bot is still admin in `CONNECTED` communities |
| `telegram_health_worker` | configurable | Bot-token health check |
| `subscription_expiry_worker` | 5 min | Queues `REMOVE_MEMBER` for expired or cancelled subscriptions |

The three Telegram workers can be disabled with `TELEGRAM_*_ENABLED=false`.

### 1.6 Documentation
- A detailed [README.md](README.md) covering architecture, models, endpoints, workflows and setup.
- Manual smoke-test scripts: [test_auth.py](test_auth.py) and [test_auth_scenarios.py](test_auth_scenarios.py). They hit a running server with `requests` and are not pytest tests.

---

## 2. Features Pending / Incomplete

### 2.1 Plans module — stub
Routes exist in [plan/routers.py](app/modules/plan/routers.py) but return hardcoded data (`[]`, `{"id": "1"}`, `"deleted"`).
- [ ] Persist plans: `PlanRepository` and `PlanService` are empty. The model has only `id`, `community_id`, `name` and `price`.
- [ ] Add duration/billing interval, currency, active flag, timestamps and a foreign key to communities.
- [ ] Add auth and ownership checks. The routes are currently unauthenticated.
- [ ] Add validation (positive price, name length) and use the real response schema (`price` is a float, not decimal/paise).
- [ ] Add plan archive instead of hard delete when subscribers exist.

### 2.2 Subscriptions module — stub
[subscription/routers.py](app/modules/subscription/routers.py) returns fake data.
- [ ] Model is minimal (`member_id`, `plan_id`, `status`). It needs start/end dates, renewal date, cancelled_at, a status enum and foreign keys.
- [ ] Implement `SubscriptionService` and repository: create, get, extend, revoke, expire.
- [ ] Add auth to the endpoints.
- [ ] Revoke and expire should trigger `TelegramService.revoke_access`.
- [ ] Subscription lifecycle rules (grace period, renewal, cancellation).

### 2.3 Members module — stub
- [ ] `GET /communities/{id}/members` returns `[]`. The service and repository are empty and the schemas file is empty.
- [ ] Model is `Member(id, community_id, telegram_user_id)` with no name, email, phone, joined_at or status. `telegram_user_id` is non-nullable in both the model and the initial migration, but the README and the linking flow treat it as nullable until a member links Telegram. It needs to become nullable.
- [ ] Member creation, onboarding and listing with filters and pagination.
- [ ] **Member authentication does not exist.** Auth covers creators only.

### 2.4 Payments (Razorpay) — PLANNED (Microservice Architecture)
**Status:** Design Phase - See [PAYMENT_MICROSERVICE_PLAN.md](PAYMENT_MICROSERVICE_PLAN.md) for detailed implementation guide

**Architecture:** Dedicated microservice (separate process on port 8769) to:
- Reduce main app tunnel bandwidth (payment data isolated)
- Enable independent scaling and deployment
- Improve security (isolated Razorpay credentials)

**Planned Features:**
- [ ] Razorpay API integration (order creation, signature verification)
- [ ] Idempotent webhook handling with UUID-based idempotency keys
- [ ] Payment event storage with retry logic and dead-letter queue
- [ ] Redis-based event publishing (payment.captured → subscription creation)
- [ ] Order creation and payment status tracking
- [ ] Webhook signature verification (HMAC-SHA256)
- [ ] Wire payment capture to subscription creation → Telegram access granting
- [ ] Refunds and failed-payment handling with notifications
- [ ] Complete database schema (payment_orders, payment_events, payment_webhooks)

**Implementation Timeline:** 3-4 weeks (4 phases)
**Dependencies:**
- Razorpay Account + API Credentials
- Redis for event queue (optional: can use DB polling)
- PostgreSQL (shared with main app)

### 2.5 Dashboard — stub
- [ ] `GET /stats` returns hardcoded `{100, 95}`. `GET /renewals` returns an empty list.
- [ ] Real aggregation queries (members, active subscriptions, revenue, churn, upcoming renewals) and creator scoping with auth.

### 2.6 Notifications — stub
- [ ] `NotificationService.send_access_granted`, `send_reminder` and `send_expiry_notice` are empty (`pass`).
- [ ] There is no router and no repository. `NotificationLog` has only `member_id` and `message_type`.
- [ ] Delivery channels (email and Telegram DM), reminder scheduling, and logging of sends.

### 2.7 Event system / queue / scheduler
- [ ] `app/events/schemas.py` defines 10 event models (`SubscriptionCreated`, `AccessGranted` and others) but nothing publishes or consumes them.
- [ ] `QueueInterface` and `SchedulerInterface` are protocols only, with no implementation. Workers use plain `asyncio` loops.
- [ ] `core/dependency.py` is an empty comment.
- [ ] Multi-instance safety for workers. There is no distributed lock or `SELECT … FOR UPDATE SKIP LOCKED`, so multiple replicas would duplicate work.

### 2.8 Telegram — remaining gaps
- [ ] **Subscription check on invite is missing.** [telegram/services.py](app/modules/telegram/services.py) `generate_invite` has a comment saying subscription validation is to be added. It currently checks only the connection and Telegram linkage. This is a functional and security gap.
- [ ] **Member endpoints use the creator JWT dependency.** `/telegram/link`, `/telegram/link/status` and `/invite` call `get_current_creator` and treat the result as `member_id`. This needs a proper member identity and auth flow.
- [ ] `CREATE_INVITE` and `SYNC_MEMBER` operation types exist, but only `REMOVE_MEMBER` and `VERIFY_CONNECTION` have executors.
- [ ] Automatic revocation on subscription expiry depends on a populated Subscription table (see 2.2).
- [ ] The sync worker checks only the bot's admin status. It does not reconcile individual members against subscriptions.
- [ ] Webhook `chat_member` events are logged only.
- [ ] Verify the production `TelegramDriver` against the real Bot API. All development has run against the stub.
- [ ] Call `setWebhook`. Registering the webhook URL and secret is not automated.

### 2.9 Cross-cutting
- [ ] **No automated test suite.** There is no pytest and no unit or integration tests. Only the two manual scripts exist, and they cover auth only. There are no tests for community, Telegram (despite a `telegram-stub-testing` skill) or the workers.
- [ ] **Alembic:** the scaffold tables (plans, subscriptions, payment_events, notification_log) exist in the initial migration. Any new columns added when those modules are built will need new migrations.
- [ ] **Repo hygiene:** `otp_dump.txt` (6 bytes) is tracked and looks like a debug leftover, so remove it or gitignore it. [generate_scaffold.py](generate_scaffold.py) is a one-off script.
- [ ] No CORS configuration, no API-level rate limiting beyond OTP, and no health or readiness endpoint.
- [ ] Add a Dockerfile, docker-compose and CI.
- [ ] Add `pytest`, `pytest-asyncio` and `requests` to `requirements.txt` as needed (`requests` is used by the scripts).
- [ ] Observability: metrics, and alerting for `FAILED` operations.

---

## 3. Suggested Build Order
1. **Plans** (real model, migration, CRUD with ownership checks).
2. **Members** (model, member auth, listing).
3. **Subscriptions** (state machine, extend and revoke wired to `TelegramService.revoke_access`).
4. **Razorpay** (order creation, signature-verified idempotent webhook, which creates a subscription and triggers access).
5. **Enforce the subscription check on Telegram invites** and move the member endpoints to member auth.
6. **Notifications** (reminders and expiry notices through the existing workers).
7. **Dashboard** aggregations.
8. **Pytest suite** (auth, community, Telegram stub, workers), CI, and a migration audit.
