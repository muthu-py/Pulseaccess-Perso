from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.modules.auth.routers import router as auth_router
from app.modules.community.routers import router as community_router
from app.modules.plan.routers import router as plan_router
from app.modules.subscription.routers import router as subscription_router
from app.modules.payment.routers import router as webhook_router
from app.modules.dashboard.routers import router as dashboard_router
from app.modules.member.routers import router as member_router
from app.modules.telegram.routers import router as telegram_router
from app.workers.telegram_retry_worker import run_retry_worker
from app.workers.telegram_sync_worker import run_sync_worker
from app.workers.telegram_health_worker import run_health_worker
from app.workers.subscription_expiry_worker import run_subscription_expiry_worker

settings = get_settings()
setup_logging(log_level=settings.LOG_LEVEL)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown events."""
    logger.info("Starting %s (%s)", settings.APP_NAME, settings.APP_ENV)

    # ── Start Telegram background workers ────────────────────────────
    tasks = [
        asyncio.create_task(run_retry_worker(), name="telegram-retry-worker"),
        asyncio.create_task(run_sync_worker(), name="telegram-sync-worker"),
        asyncio.create_task(run_health_worker(), name="telegram-health-worker"),
        asyncio.create_task(
            run_subscription_expiry_worker(), name="subscription-expiry-worker"
        ),
    ]
    logger.info("Telegram background workers started (%d tasks)", len(tasks))

    yield

    # ── Graceful shutdown: cancel all worker tasks ───────────────────
    logger.info("Shutting down %s — cancelling background workers", settings.APP_NAME)
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("Background workers stopped")


app = FastAPI(
    title=f"{settings.APP_NAME} API",
    debug=settings.APP_DEBUG,
    lifespan=lifespan,
)

# Register global exception handlers
register_exception_handlers(app)

# Register routers
app.include_router(auth_router)
app.include_router(community_router)
app.include_router(plan_router)
app.include_router(subscription_router)
app.include_router(webhook_router)
app.include_router(dashboard_router)
app.include_router(member_router)
app.include_router(telegram_router)


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME} API"}
