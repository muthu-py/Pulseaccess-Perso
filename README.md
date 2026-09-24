# PulseAccess

PulseAccess is a **FastAPI-based backend** built with a **modular monolith architecture**. It manages creators, communities, subscription plans, members, and Telegram-based access control — with full async database operations and background worker orchestration.

---

## Architecture Overview

The project enforces a strict layered architecture with one-way dependency flow:

```
Router → Service → Repository / Infrastructure
```

| Layer | Path | Responsibility |
|-------|------|----------------|
| **Routers** | `app/modules/*/routers.py` | Endpoint definitions, request validation, auth/authz, delegation to service. No SQL, no business logic. |
| **Services** | `app/modules/*/services.py` | All business logic, workflow orchestration, state transitions. |
| **Repositories** | `app/modules/*/repositories.py` | Data persistence and ORM queries only. No business logic, no HTTP calls. |
| **Infrastructure** | `app/infrastructure/` | Protocol translation, external API clients (Telegram, Email, Razorpay). No business logic. |
| **Workers** | `app/workers/` | Background async tasks. Call services — never repositories or infrastructure directly. |

---

## Module Map

```
app/
├── main.py                        # FastAPI app factory, lifespan, router registration
├── core/
│   ├── config.py                  # Settings via pydantic-settings (env-driven)
│   ├── exceptions.py              # Global exception handlers
│   ├── logging.py                 # Structured logging setup
│   └── security.py                # HMAC-SHA256 hashing utilities
├── api/
│   └── dependencies.py            # Shared FastAPI dependencies (get_current_creator, etc.)
├── infrastructure/
│   ├── database/                  # AsyncSession, SQLAlchemy engine, Base
│   ├── email/                     # aiosmtplib SMTP client
│   ├── security/                  # JWT issuance and validation
│   ├── telegram/                  # TelegramClient protocol, TelegramDriver, TelegramStub
│   ├── razorpay/                  # Payment gateway stub
│   ├── queue/                     # Operation queue utilities
│   └── scheduler/                 # Scheduler helpers
├── modules/
│   ├── auth/                      # Passwordless OTP auth (Creator accounts)
│   ├── community/                 # Community CRUD + lifecycle management
│   ├── plan/                      # Subscription plan scaffold (stub)
│   ├── subscription/              # Subscription model and schemas
│   ├── member/                    # Member scaffold (stub)
│   ├── payment/                   # Razorpay webhook scaffold (stub)
│   ├── dashboard/                 # Dashboard stats scaffold (stub)
│   ├── notification/              # Notification scaffold
│   └── telegram/                  # Telegram integration (full implementation)
└── workers/
    ├── telegram_retry_worker.py   # Processes pending Telegram operations (60s interval)
    ├── telegram_sync_worker.py    # Reconciles PulseAccess ↔ Telegram membership (5min interval)
    ├── telegram_health_worker.py  # Periodic bot connectivity health check
    └── subscription_expiry_worker.py # Queues member removals for expired subscriptions (5min interval)
```

---

## Database Models

### `creators` — Creator accounts
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `name` | String(255) | |
| `username` | String(100) | Unique |
| `email` | String(255) | Unique |
| `is_active` | Boolean | Default true |
| `created_at` | DateTime (TZ) | |

### `login_otps` — Passwordless OTP records
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `creator_id` | UUID FK → creators | CASCADE delete |
| `otp_hash` | String(255) | HMAC-SHA256 hash, never plaintext |
| `purpose` | String(50) | Default "login" |
| `attempts` | Integer | Incremented on each failed attempt |
| `expires_at` | DateTime (TZ) | 5 minutes from creation |
| `used_at` | DateTime (TZ) | Nullable; set on successful verification |
| `created_at` | DateTime (TZ) | |

### `refresh_tokens` — Active sessions
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `creator_id` | UUID FK → creators | CASCADE delete |
| `token_hash` | String(255) | HMAC-SHA256 hash |
| `expires_at` | DateTime (TZ) | 30 days |
| `revoked_at` | DateTime (TZ) | Nullable; set on logout or token rotation |
| `created_at` | DateTime (TZ) | |

### `communities` — Creator-owned groups
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `creator_id` | UUID | |
| `name` | String(255) | Unique per creator |
| `is_active` | Boolean | Default true |
| `created_at` / `updated_at` | DateTime (TZ) | |
| `telegram_chat_id` | String(100) | Nullable; set when connected |
| `telegram_connection_status` | String(20) | Enum: NOT_CONNECTED, CONNECTING, CONNECTED, NEEDS_ATTENTION, DISCONNECTED |
| `telegram_connected_at` | DateTime (TZ) | Nullable |

### `members` — Community subscribers
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `community_id` | UUID | |
| `telegram_user_id` | String | Nullable; set after Telegram linking |

### `telegram_operations` — Async operation queue
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `operation_type` | String(50) | Enum: CREATE_INVITE, REMOVE_MEMBER, VERIFY_CONNECTION, SYNC_MEMBER |
| `community_id` | UUID FK → communities | CASCADE delete |
| `member_id` | UUID FK → members | SET NULL on delete |
| `status` | String(20) | Enum: PENDING, PROCESSING, COMPLETED, RETRYING, FAILED |
| `retry_count` | Integer | Default 0 |
| `last_error` | Text | Nullable |
| `scheduled_at` | DateTime (TZ) | Nullable; future time for retries |
| `completed_at` / `created_at` | DateTime (TZ) | |

---

## API Endpoints

### Auth — `/api/v1/auth`

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/register` | Create a new Creator account. Validates email and username uniqueness. |
| `POST` | `/request-otp` | Send a 6-digit OTP to the creator's email. Always returns generic success (anti-enumeration). |
| `POST` | `/verify-otp` | Verify OTP (5 attempts max, 5-min expiry). Issues Access Token (JSON) + Refresh Token (HttpOnly cookie). |
| `POST` | `/refresh` | Rotate tokens: reads HttpOnly cookie, revokes old token, issues new pair. |
| `POST` | `/logout` | Revoke session in DB and clear the HttpOnly cookie. |

### Communities — `/api/v1/communities`
> All endpoints require Bearer JWT (`Authorization: Bearer <access_token>`).

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/` | Create a new community (name unique per creator, 3–100 chars). |
| `GET` | `/active` | List active communities (paginated). |
| `GET` | `/inactive` | List inactive communities (paginated). |
| `GET` | `/{community_id}` | Get a single community by ID. |
| `PATCH` | `/{community_id}` | Update community name. |
| `PATCH` | `/{community_id}/activate` | Set community to active. |
| `PATCH` | `/{community_id}/deactivate` | Set community to inactive (Telegram connection unaffected). |

### Plans — `/api/v1/communities/{id}/plans` *(scaffold)*

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/communities/{id}/plans` | List plans for a community. |
| `POST` | `/api/v1/communities/{id}/plans` | Create a plan. |
| `PUT` | `/api/v1/plans/{id}` | Update a plan. |
| `DELETE` | `/api/v1/plans/{id}` | Delete a plan. |

### Dashboard — `/api/v1/dashboard` *(scaffold)*

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/stats` | Returns summary stats (total members, active subscriptions). |
| `GET` | `/renewals` | Returns upcoming subscription renewals. |

### Members — *(scaffold)*

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/communities/{id}/members` | List members for a community. |

### Telegram Integration — `/api/v1/telegram`
> Creator endpoints require Bearer JWT. Webhook uses `X-Telegram-Bot-Api-Secret-Token` header only.

#### Creator Endpoints
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/telegram/communities/{community_id}/connect` | Generate a temporary connection code for linking a Telegram group. Sets status to `CONNECTING`. |
| `GET` | `/api/v1/telegram/communities/{community_id}/status` | Get the current Telegram connection status and `chat_id`. |
| `DELETE` | `/api/v1/telegram/communities/{community_id}` | Disconnect Telegram from a community (no business data deleted). |

#### Member Endpoints
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/telegram/link` | Generate a Telegram deep-link (`t.me/bot?start=...`) for account linking. |
| `GET` | `/api/v1/telegram/link/status` | Check if the authenticated member has a linked Telegram account. |
| `POST` | `/api/v1/telegram/communities/{community_id}/invite` | Generate a temporary Telegram group invite link. Requires active subscription and linked Telegram account. |

#### Webhook
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/webhooks/telegram` | Receives Telegram Bot updates. Secret verified first, then dispatches to `message`, `my_chat_member`, or `chat_member` handlers. |

---

## Telegram Integration — Workflows

The Telegram module implements 6 primary workflows:

1. **Community Connection**: Creator generates a connection code → bot is added to group → webhook `my_chat_member` event fires → status transitions to `CONNECTED`.
2. **Account Linking**: Member requests a deep link → clicks link → Telegram `/start` webhook fires → `telegram_user_id` stored against member record.
3. **Invite Generation**: Validates community is `CONNECTED` and member has a linked Telegram account → calls `TelegramClient.create_invite_link()` with 1-use, time-limited parameters.
4. **Access Revocation**: Queues a `REMOVE_MEMBER` operation into `telegram_operations`. Retry worker executes it asynchronously (ban + unban pattern).
5. **Synchronization**: Sync worker periodically checks all `CONNECTED` communities to verify the bot is still an administrator. Sets status to `NEEDS_ATTENTION` if removed.
6. **Webhook Processing**: Routes three Telegram update types:
   - `message` → handles `/start` deep links for account linking.
   - `my_chat_member` → tracks bot added/removed/promoted events, updates community status.
   - `chat_member` → logs member join/leave events for reconciliation.

### Connection Status Lifecycle
```
NOT_CONNECTED → CONNECTING → CONNECTED → NEEDS_ATTENTION
                                       ↘ DISCONNECTED
```

### Operation Queue — Retry Logic
Failed operations use exponential backoff:

| Retry # | Delay |
|---------|-------|
| 1 | 1 min |
| 2 | 5 min |
| 3 | 15 min |
| 4 | 30 min |
| 5 | 60 min |

Permanent failures (`TelegramNotFoundException`, `TelegramPermissionException`) skip retries and move directly to `FAILED`.

### Infrastructure — `TelegramClient` Protocol
The service layer depends on the `TelegramClient` protocol, never on the concrete driver:

| Implementation | Used When |
|----------------|-----------|
| `TelegramDriver` | Production (`APP_ENV != development`). Uses `httpx.AsyncClient`. |
| `TelegramStub` | Development and testing. Returns realistic fake responses without calling Telegram. |

---

## Background Workers

All workers start at application startup via the FastAPI `lifespan` context and are cancelled gracefully on shutdown.

| Worker | Interval | Responsibility |
|--------|----------|----------------|
| `telegram_retry_worker` | 60 seconds | Processes all `PENDING` / `RETRYING` operations from `telegram_operations`. |
| `telegram_sync_worker` | 5 minutes | Verifies bot admin status in all `CONNECTED` communities. |
| `telegram_health_worker` | Configurable | Calls `TelegramClient.health_check()` to confirm bot token is valid. |
| `subscription_expiry_worker` | 5 minutes | Finds expired/cancelled subscriptions and queues `REMOVE_MEMBER` operations for members with linked Telegram accounts. |

Workers can be individually disabled via environment variables:
```env
TELEGRAM_RETRY_ENABLED=false
TELEGRAM_SYNC_ENABLED=false
TELEGRAM_HEALTH_ENABLED=false
```

---

## Authentication Design

The system uses a **Passwordless (OTP-based)** flow:

- **No passwords stored** — login is entirely via 6-digit OTPs emailed to the creator.
- **Dual-token strategy**:
  - **Access Token** (15 min): Returned in the JSON response body. Used as `Bearer` token for API calls.
  - **Refresh Token** (30 days): Set as `HttpOnly, SameSite=Lax` cookie. Never readable by JavaScript (XSS mitigation).
- **HMAC-SHA256 hashing**: Both OTPs and refresh tokens are hashed before persistence. Plaintext is never stored.
- **Token rotation**: Each `/refresh` call revokes the old token and issues a new pair.
- **Anti-enumeration**: `/request-otp` always returns a generic success response, even for unknown emails.
- **Brute-force protection**: OTPs expire after 5 minutes and are locked after 5 failed attempts.
- **Rate limiting**: OTP requests are limited to 5 per 15-minute window per account.

---

## Local Development Setup

### 1. Requirements
- Python 3.12+
- PostgreSQL 14+

### 2. Environment Variables

Create a `.env` file in the project root (see full variable reference above in the Environment Variables section).

Key required variables:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/pulseaccess
JWT_SECRET_KEY=your_jwt_secret_at_least_32_chars
OTP_HASH_SECRET=your_otp_hmac_secret_at_least_32_chars
SMTP_HOST=smtp.gmail.com
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
TELEGRAM_BOT_TOKEN=123456:ABCdef...
TELEGRAM_BOT_USERNAME=your_bot_username
TELEGRAM_WEBHOOK_SECRET=your_webhook_secret
```

### 3. Installation

```bash
pip install -r requirements.txt
```

**Dependencies:**

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | >=0.115.0 | Web framework |
| `uvicorn[standard]` | >=0.30.0 | ASGI server |
| `sqlalchemy[asyncio]` | >=2.0.30 | Async ORM |
| `asyncpg` | >=0.29.0 | PostgreSQL async driver |
| `alembic` | >=1.13.0 | Database migrations |
| `pydantic` | >=2.7.0 | Data validation |
| `pydantic-settings` | >=2.3.0 | Settings management |
| `python-jose[cryptography]` | >=3.3.0 | JWT encoding/decoding |
| `aiosmtplib` | >=3.0.0 | Async SMTP email |
| `email-validator` | >=2.1.0 | Email format validation |
| `python-dotenv` | >=1.0.0 | `.env` file loading |
| `httpx` | >=0.27.0 | Async HTTP client (Telegram API) |

### 4. Database Migrations

```bash
# Generate migrations from ORM models
alembic revision --autogenerate -m "Initial migration"

# Apply to database
alembic upgrade head
```

### 5. Running the Server

```bash
uvicorn app.main:app --reload
```

- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## Security Rules

- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, and JWT secrets **must never** be hardcoded, logged, or returned in API payloads.
- Webhook endpoints verify `TELEGRAM_WEBHOOK_SECRET` **before** any JSON parsing or business logic execution.
- All Telegram API calls use `httpx.AsyncClient`. The `python-telegram-bot` and `aiogram` libraries are **not used**.
- Database transactions are kept short. HTTP calls are **never** made inside a transaction.

---

## Development Notes

- In `APP_ENV=development`, workers automatically use `TelegramStub` instead of `TelegramDriver` — no real bot token needed for local testing.
- `DATABASE_URL` is automatically rewritten from `postgresql://` to `postgresql+asyncpg://` for async compatibility.
- All async DB queries use SQLAlchemy 2.0 syntax (`select()`, `update()`, `AsyncSession`).
- PostgreSQL is always the **source of truth**. Telegram reflects business state — it does not drive it.
