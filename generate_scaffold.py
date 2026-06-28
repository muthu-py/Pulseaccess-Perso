import os

def create_file(path, content):
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(path, "w") as f:
        f.write(content.strip() + "\n")

# core
create_file("app/core/__init__.py", "")
create_file("app/core/config.py", """
class Settings:
    pass
settings = Settings()
""")
create_file("app/core/security.py", """
def get_password_hash(password: str) -> str:
    pass

def verify_password(plain_password: str, hashed_password: str) -> bool:
    pass
""")
create_file("app/core/constants.py", """
APP_NAME = "PulseAccess"
""")
create_file("app/core/exceptions.py", """
class PulseAccessException(Exception):
    pass
""")
create_file("app/core/dependency.py", """
# Core dependencies
""")
create_file("app/core/logging.py", """
import logging

def setup_logging():
    pass
""")

# infrastructure
create_file("app/infrastructure/__init__.py", "")
create_file("app/infrastructure/database/__init__.py", "")
create_file("app/infrastructure/database/base.py", """
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
""")
create_file("app/infrastructure/database/session.py", """
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

async def get_db():
    async with SessionLocal() as session:
        yield session
""")

create_file("app/infrastructure/telegram/__init__.py", "")
create_file("app/infrastructure/telegram/telegram_interface.py", """
from typing import Protocol

class TelegramService(Protocol):
    async def grant_access(self, user_id: str, channel_id: str) -> None:
        ...

    async def revoke_access(self, user_id: str, channel_id: str) -> None:
        ...

    async def send_message(self, user_id: str, message: str) -> None:
        ...

    async def create_invite_link(self, channel_id: str) -> str:
        ...
""")
create_file("app/infrastructure/telegram/telegram_stub.py", """
from app.infrastructure.telegram.telegram_interface import TelegramService

class TelegramStub(TelegramService):
    async def grant_access(self, user_id: str, channel_id: str) -> None:
        pass

    async def revoke_access(self, user_id: str, channel_id: str) -> None:
        pass

    async def send_message(self, user_id: str, message: str) -> None:
        pass

    async def create_invite_link(self, channel_id: str) -> str:
        return "https://t.me/joinchat/stub"
""")

create_file("app/infrastructure/razorpay/__init__.py", "")
create_file("app/infrastructure/razorpay/razorpay_interface.py", """
from typing import Protocol

class RazorpayService(Protocol):
    async def process_webhook(self, payload: dict, signature: str) -> bool:
        ...
""")
create_file("app/infrastructure/razorpay/razorpay_stub.py", """
from app.infrastructure.razorpay.razorpay_interface import RazorpayService

class RazorpayStub(RazorpayService):
    async def process_webhook(self, payload: dict, signature: str) -> bool:
        return True
""")

create_file("app/infrastructure/queue/__init__.py", "")
create_file("app/infrastructure/queue/queue_interface.py", """
from typing import Protocol

class QueueInterface(Protocol):
    async def enqueue(self, task_name: str, payload: dict) -> None:
        ...
""")

create_file("app/infrastructure/scheduler/__init__.py", "")
create_file("app/infrastructure/scheduler/scheduler_interface.py", """
from typing import Protocol

class SchedulerInterface(Protocol):
    async def schedule(self, task_name: str, run_at: str, payload: dict) -> None:
        ...
""")

# events
create_file("app/events/__init__.py", "")
create_file("app/events/schemas.py", """
from pydantic import BaseModel

class CreatorRegistered(BaseModel):
    creator_id: str

class CommunityCreated(BaseModel):
    community_id: str

class PlanCreated(BaseModel):
    plan_id: str

class PaymentCaptured(BaseModel):
    payment_id: str

class SubscriptionCreated(BaseModel):
    subscription_id: str

class SubscriptionExtended(BaseModel):
    subscription_id: str

class SubscriptionExpired(BaseModel):
    subscription_id: str

class AccessGranted(BaseModel):
    member_id: str

class AccessRevoked(BaseModel):
    member_id: str

class ReminderSent(BaseModel):
    member_id: str
""")

# modules templates
modules = ["auth", "community", "plan", "member", "subscription", "payment", "telegram", "notification", "dashboard"]
for mod in modules:
    create_file(f"app/modules/{mod}/__init__.py", "")
    create_file(f"app/modules/{mod}/models.py", "from sqlalchemy.orm import Mapped, mapped_column\nfrom app.infrastructure.database.base import Base\nimport uuid")
    create_file(f"app/modules/{mod}/schemas.py", "from pydantic import BaseModel")
    create_file(f"app/modules/{mod}/repositories.py", "")
    create_file(f"app/modules/{mod}/services.py", "")
    create_file(f"app/modules/{mod}/routers.py", "from fastapi import APIRouter\n\nrouter = APIRouter()")

# specific module content
# auth
create_file("app/modules/auth/models.py", """
import uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database.base import Base

class Creator(Base):
    __tablename__ = "creators"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str]
    hashed_password: Mapped[str]

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    creator_id: Mapped[uuid.UUID]
    token: Mapped[str]
""")
create_file("app/modules/auth/schemas.py", """
from pydantic import BaseModel

class RegisterRequest(BaseModel):
    email: str
    password: str

class RegisterResponse(BaseModel):
    id: str
    email: str

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str

class RefreshRequest(BaseModel):
    refresh_token: str

class RefreshResponse(BaseModel):
    access_token: str
""")
create_file("app/modules/auth/repositories.py", """
class CreatorRepository:
    pass

class RefreshTokenRepository:
    pass
""")
create_file("app/modules/auth/services.py", """
class AuthService:
    pass
""")
create_file("app/modules/auth/routers.py", """
from fastapi import APIRouter
from app.modules.auth.schemas import RegisterRequest, RegisterResponse, LoginRequest, LoginResponse, RefreshRequest, RefreshResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.post("/register", response_model=RegisterResponse)
async def register(request: RegisterRequest):
    return {"id": "test_id", "email": "test@example.com"}

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    return {"access_token": "token", "refresh_token": "refresh"}

@router.post("/refresh", response_model=RefreshResponse)
async def refresh(request: RefreshRequest):
    return {"access_token": "new_token"}

@router.post("/logout")
async def logout():
    return {"status": "ok"}
""")

# community
create_file("app/modules/community/models.py", """
import uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database.base import Base

class Community(Base):
    __tablename__ = "communities"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    creator_id: Mapped[uuid.UUID]
    name: Mapped[str]
    telegram_channel_id: Mapped[str]
""")
create_file("app/modules/community/schemas.py", """
from pydantic import BaseModel

class CreateCommunityRequest(BaseModel):
    name: str

class CommunityResponse(BaseModel):
    id: str
    name: str
""")
create_file("app/modules/community/repositories.py", """
class CommunityRepository:
    pass
""")
create_file("app/modules/community/services.py", """
class CommunityService:
    pass
""")
create_file("app/modules/community/routers.py", """
from fastapi import APIRouter
from app.modules.community.schemas import CreateCommunityRequest, CommunityResponse

router = APIRouter(prefix="/api/v1/communities", tags=["communities"])

@router.get("")
async def get_communities():
    return []

@router.post("", response_model=CommunityResponse)
async def create_community(request: CreateCommunityRequest):
    return {"id": "1", "name": request.name}

@router.get("/{id}")
async def get_community(id: str):
    return {"id": id, "name": "Test"}

@router.delete("/{id}")
async def delete_community(id: str):
    return {"status": "deleted"}
""")

# plan
create_file("app/modules/plan/models.py", """
import uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database.base import Base

class Plan(Base):
    __tablename__ = "plans"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    community_id: Mapped[uuid.UUID]
    name: Mapped[str]
    price: Mapped[float]
""")
create_file("app/modules/plan/schemas.py", """
from pydantic import BaseModel

class CreatePlanRequest(BaseModel):
    name: str
    price: float

class UpdatePlanRequest(BaseModel):
    name: str
    price: float

class PlanResponse(BaseModel):
    id: str
    name: str
    price: float
""")
create_file("app/modules/plan/repositories.py", """
class PlanRepository:
    pass
""")
create_file("app/modules/plan/services.py", """
class PlanService:
    pass
""")
create_file("app/modules/plan/routers.py", """
from fastapi import APIRouter
from app.modules.plan.schemas import CreatePlanRequest, UpdatePlanRequest, PlanResponse

router = APIRouter(tags=["plans"])

@router.get("/api/v1/communities/{id}/plans")
async def get_plans(id: str):
    return []

@router.post("/api/v1/communities/{id}/plans", response_model=PlanResponse)
async def create_plan(id: str, request: CreatePlanRequest):
    return {"id": "1", "name": request.name, "price": request.price}

@router.put("/api/v1/plans/{id}", response_model=PlanResponse)
async def update_plan(id: str, request: UpdatePlanRequest):
    return {"id": id, "name": request.name, "price": request.price}

@router.delete("/api/v1/plans/{id}")
async def delete_plan(id: str):
    return {"status": "deleted"}
""")

# member
create_file("app/modules/member/models.py", """
import uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database.base import Base

class Member(Base):
    __tablename__ = "members"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    community_id: Mapped[uuid.UUID]
    telegram_user_id: Mapped[str]
""")
create_file("app/modules/member/repositories.py", """
class MemberRepository:
    pass
""")
create_file("app/modules/member/services.py", """
class MemberService:
    pass
""")
create_file("app/modules/member/routers.py", """
from fastapi import APIRouter

router = APIRouter(tags=["members"])

@router.get("/api/v1/communities/{id}/members")
async def get_members(id: str):
    return []
""")

# subscription
create_file("app/modules/subscription/models.py", """
import uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database.base import Base

class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    member_id: Mapped[uuid.UUID]
    plan_id: Mapped[uuid.UUID]
    status: Mapped[str]
""")
create_file("app/modules/subscription/schemas.py", """
from pydantic import BaseModel

class SubscriptionResponse(BaseModel):
    id: str
    status: str

class ExtendSubscriptionRequest(BaseModel):
    days: int
""")
create_file("app/modules/subscription/repositories.py", """
class SubscriptionRepository:
    pass
""")
create_file("app/modules/subscription/services.py", """
class SubscriptionService:
    pass
""")
create_file("app/modules/subscription/routers.py", """
from fastapi import APIRouter
from app.modules.subscription.schemas import SubscriptionResponse, ExtendSubscriptionRequest

router = APIRouter(prefix="/api/v1/subscriptions", tags=["subscriptions"])

@router.get("/{id}")
async def get_subscription(id: str):
    return {"id": id, "status": "active"}

@router.post("/{id}/extend")
async def extend_subscription(id: str, request: ExtendSubscriptionRequest):
    return {"status": "extended"}

@router.post("/{id}/revoke")
async def revoke_subscription(id: str):
    return {"status": "revoked"}
""")

# payment
create_file("app/modules/payment/models.py", """
import uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database.base import Base

class PaymentEvent(Base):
    __tablename__ = "payment_events"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    payload: Mapped[str]
""")
create_file("app/modules/payment/repositories.py", """
class PaymentEventRepository:
    pass
""")
create_file("app/modules/payment/services.py", """
class PaymentService:
    pass
""")
create_file("app/modules/payment/routers.py", """
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

@router.post("/razorpay")
async def razorpay_webhook():
    return {"status": "received"}
""")

# notification
create_file("app/modules/notification/models.py", """
import uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database.base import Base

class NotificationLog(Base):
    __tablename__ = "notification_log"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    member_id: Mapped[uuid.UUID]
    message_type: Mapped[str]
""")
create_file("app/modules/notification/repositories.py", """
class NotificationRepository:
    pass
""")
create_file("app/modules/notification/services.py", """
class NotificationService:
    async def send_access_granted(self):
        pass

    async def send_reminder(self):
        pass

    async def send_expiry_notice(self):
        pass
""")

# dashboard
create_file("app/modules/dashboard/schemas.py", """
from pydantic import BaseModel

class DashboardStatsResponse(BaseModel):
    total_members: int
    active_subscriptions: int

class UpcomingRenewalsResponse(BaseModel):
    renewals: list
""")
create_file("app/modules/dashboard/services.py", """
class DashboardService:
    pass
""")
create_file("app/modules/dashboard/routers.py", """
from fastapi import APIRouter
from app.modules.dashboard.schemas import DashboardStatsResponse, UpcomingRenewalsResponse

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

@router.get("/stats", response_model=DashboardStatsResponse)
async def get_stats():
    return {"total_members": 100, "active_subscriptions": 95}

@router.get("/renewals", response_model=UpcomingRenewalsResponse)
async def get_renewals():
    return {"renewals": []}
""")

# dependencies
create_file("app/api/__init__.py", "")
create_file("app/api/dependencies.py", """
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.session import get_db
from app.modules.auth.services import AuthService
from app.modules.community.services import CommunityService
from app.modules.plan.services import PlanService
from app.modules.subscription.services import SubscriptionService
from app.infrastructure.telegram.telegram_interface import TelegramService
from app.infrastructure.telegram.telegram_stub import TelegramStub
from app.infrastructure.razorpay.razorpay_interface import RazorpayService
from app.infrastructure.razorpay.razorpay_stub import RazorpayStub

def get_auth_service() -> AuthService:
    return AuthService()

def get_community_service() -> CommunityService:
    return CommunityService()

def get_plan_service() -> PlanService:
    return PlanService()

def get_subscription_service() -> SubscriptionService:
    return SubscriptionService()

def get_telegram_service() -> TelegramService:
    return TelegramStub()

def get_razorpay_service() -> RazorpayService:
    return RazorpayStub()
""")

# main
create_file("app/main.py", """
from fastapi import FastAPI
from app.modules.auth.routers import router as auth_router
from app.modules.community.routers import router as community_router
from app.modules.plan.routers import router as plan_router
from app.modules.subscription.routers import router as subscription_router
from app.modules.payment.routers import router as webhook_router
from app.modules.dashboard.routers import router as dashboard_router
from app.modules.member.routers import router as member_router

app = FastAPI(title="PulseAccess API")

app.include_router(auth_router)
app.include_router(community_router)
app.include_router(plan_router)
app.include_router(subscription_router)
app.include_router(webhook_router)
app.include_router(dashboard_router)
app.include_router(member_router)

@app.get("/")
async def root():
    return {"message": "Welcome to PulseAccess API"}
""")

# alembic
create_file("alembic.ini", """
[alembic]
script_location = alembic
sqlalchemy.url = postgresql+asyncpg://user:pass@localhost/db
""")
create_file("alembic/env.py", """
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from app.infrastructure.database.base import Base

import app.modules.auth.models
import app.modules.community.models
import app.modules.plan.models
import app.modules.member.models
import app.modules.subscription.models
import app.modules.payment.models
import app.modules.notification.models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    pass

def run_migrations_online() -> None:
    pass
""")
create_file("alembic/script.py.mako", """
\"\"\"${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

\"\"\"
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
""")
