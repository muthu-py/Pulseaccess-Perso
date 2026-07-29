---
name: telegram-stub-testing
description: Testing strategies, pytest patterns, and stubbing rules for PulseAccess Telegram integration components.
---

# Telegram Stub & Unit Testing Skill

## Overview
Guidelines for writing pytest test cases for the PulseAccess Telegram module using `TelegramStub`.

## Key Testing Principles
1. **Never Contact Live Telegram**: All unit and integration tests MUST use `TelegramStub` or pytest mocks.
2. **Deterministic Responses**: `TelegramStub` returns predictable test data (e.g. stubbed invite links, chat IDs).
3. **Database Isolation**: Tests run against an isolated test database session or rollback after execution.
4. **Service Level Testing**: Test `TelegramService` methods for success cases, validation errors, and retry queuing.

## Standard Test Suite Structure
- `app/tests/telegram/test_infrastructure.py`: Test driver mapper, exception translation, and stub responses.
- `app/tests/telegram/test_service.py`: Business service unit tests for community connect, link, invite, revoke.
- `app/tests/telegram/test_routers.py`: API endpoint response format, status codes, and authorization.
- `app/tests/telegram/test_workers.py`: Background worker queue execution, backoff scheduling, and crash recovery.
