# PulseAccess Agent Guidance & Project Rules

## Architecture Rules & Layer Invariants
1. **Source of Truth**: PulseAccess (PostgreSQL) is ALWAYS the source of truth. Telegram only reflects business state.
2. **Layer Separation**:
   - **Routers** (`app/modules/*/routers.py`): Endpoint definitions, request validation, auth/authz checks, delegation to services. NO SQL, NO business logic, NO Telegram API calls.
   - **Services** (`app/modules/*/services.py`): ALL business logic, workflow orchestration, validation rules, state transitions.
   - **Repositories** (`app/modules/*/repositories.py`): Data persistence and ORM queries only. NO business logic, NO external HTTP calls.
   - **Infrastructure** (`app/infrastructure/`): Protocol translation, external HTTP APIs (Telegram, Email, Razorpay). NO business logic.
   - **Workers** (`app/workers/`): Background execution of queued operations. MUST call services, NOT repositories or raw infrastructure directly.
3. **Dependency Flow**: Always downward: `Router -> Service -> Repository / Infrastructure`. Reverse dependencies are strictly prohibited.

## Security & Secrets
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, and JWT secrets MUST NEVER be hardcoded, logged, or returned in API payloads.
- Use `httpx.AsyncClient` for Telegram API calls. Do NOT use `python-telegram-bot` or `aiogram`.
- Webhook endpoints MUST verify `TELEGRAM_WEBHOOK_SECRET` before parsing or processing.

## Database & Asynchronous Design
- All database interactions must use SQLAlchemy 2.0 async syntax (`select()`, `update()`, `delete()`, `AsyncSession`).
- Async background workers must handle failures idempotently with exponential backoff.
- Transactions must remain short. Never perform HTTP calls inside database transactions.
