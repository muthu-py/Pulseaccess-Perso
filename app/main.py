from contextlib import asynccontextmanager

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

settings = get_settings()
setup_logging(log_level=settings.LOG_LEVEL)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown events."""
    logger.info("Starting %s (%s)", settings.APP_NAME, settings.APP_ENV)
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


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


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME} API"}
