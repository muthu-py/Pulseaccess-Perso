---
name: fastapi-sqlalchemy-patterns
description: Coding standards and patterns for FastAPI, Async SQLAlchemy 2.0, Pydantic v2, and Alembic in the PulseAccess codebase.
---

# FastAPI & SQLAlchemy 2.0 Async Patterns Skill

## Overview
This skill defines exact code style and architectural patterns used across PulseAccess.

## 1. SQLAlchemy 2.0 Async Models
- Use `Mapped[T]` and `mapped_column()` annotations.
- UUID primary keys default to `uuid.uuid4`.
- Explicitly define foreign key constraints with `ondelete` rules.
- Explicitly define indexes in `__table_args__`.

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database.base import Base

class TelegramOperation(Base):
    __tablename__ = "telegram_operations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    community_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("communities.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
```

## 2. Pydantic v2 Schemas
- Use `ConfigDict(from_attributes=True)` for response models.
- Wrap API responses in `BaseSuccessResponse[T]`.
- Field validation must use standard `pydantic` constructs (`Field`, `EmailStr`).

## 3. Repository Pattern
- Repositories accept `AsyncSession` in `__init__`.
- Use `select()`, `update()`, `delete()` with `await self._session.execute()`.
- Return domain models or ORM entities.

## 4. FastAPI Dependency Injection
- Define reusable dependency factories in `app/api/dependencies.py` or module-specific `dependencies.py`.
- Service dependencies inject repositories, settings, and infrastructure clients.
