---
name: telegram-integration-execution
description: Execution roadmap, phase order, and verification rules for implementing the PulseAccess Telegram integration pack.
---

# Telegram Integration Execution Skill

## Overview
This skill guides the step-by-step implementation of the Telegram integration pack (`telegram-integration-pack/00_READ_FIRST.md` through `15_Developer_Guardrails.md`).

## Phase Execution Checklist

### Phase 1: Database Migration (Doc 03)
- [ ] Rename `telegram_channel_id` to `telegram_chat_id` on `Community` model (`app/modules/community/models.py`).
- [ ] Add `telegram_connection_status` and `telegram_connected_at` columns to `Community`.
- [ ] Create `TelegramOperation` model in `app/modules/telegram/models.py` mapping to table `telegram_operations`.
- [ ] Generate and verify Alembic migration script supporting upgrade and downgrade.

### Phase 2: Infrastructure Layer (Doc 04)
- [ ] Define `TelegramClient` Protocol in `app/infrastructure/telegram/telegram_interface.py`.
- [ ] Implement `TelegramDriver` in `app/infrastructure/telegram/telegram_driver.py` using `httpx.AsyncClient`.
- [ ] Implement `TelegramStub` in `app/infrastructure/telegram/telegram_stub.py`.
- [ ] Add DTO models (`telegram_models.py`), exception hierarchy (`telegram_exceptions.py`), and mapper (`telegram_mapper.py`).

### Phase 3: Business Module (Doc 05)
- [ ] Create domain enums in `app/modules/telegram/enums.py` (`TelegramConnectionStatus`, `TelegramOperationType`, `TelegramOperationStatus`).
- [ ] Create business exceptions in `app/modules/telegram/exceptions.py`.
- [ ] Implement `TelegramRepository` in `app/modules/telegram/repositories.py`.
- [ ] Implement `TelegramService` in `app/modules/telegram/services.py` handling community connection, account linking, invite generation, revocation, and queue operations.
- [ ] Define Pydantic v2 schemas in `app/modules/telegram/schemas.py`.

### Phase 4: REST API (Doc 06)
- [ ] Implement Creator APIs (`POST /connect`, `GET /status`, `DELETE /`) in `app/modules/telegram/routers.py`.
- [ ] Implement Member APIs (`POST /link`, `GET /link/status`, `POST /invite`).
- [ ] Register JWT dependencies (`get_current_creator`, `get_current_member`) in `app/api/dependencies.py`.
- [ ] Mount Telegram router in `app/main.py`.

### Phase 5: Webhook Subsystem (Doc 07)
- [ ] Implement `POST /api/v1/webhooks/telegram` endpoint.
- [ ] Verify `X-Telegram-Bot-Api-Secret-Token` header.
- [ ] Dispatch supported events (`message`, `my_chat_member`, `chat_member`) to `TelegramService`.
- [ ] Safely log and ignore unsupported updates with `200 OK`.

### Phase 6: Background Workers (Doc 08 & 09)
- [ ] Implement `telegram_retry_worker.py` with exponential backoff and `SELECT FOR UPDATE SKIP LOCKED`.
- [ ] Implement `telegram_sync_worker.py` for membership reconciliation.
- [ ] Implement `telegram_health_worker.py` for bot connectivity checks.
- [ ] Implement `subscription_expiry_worker.py` to queue member removals on subscription expiration.

### Phase 7: Verification & Testing (Doc 11 & 14)
- [ ] Run test suite with pytest using `TelegramStub`.
- [ ] Ensure 100% compliance with `14_Acceptance_Checklist.md`.
