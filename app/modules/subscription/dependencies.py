"""FastAPI dependencies for subscription repository and service injection."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_db
from app.modules.subscription.repositories import SubscriptionRepository
from app.modules.subscription.services import SubscriptionService


def get_subscription_repository(
    session: AsyncSession = Depends(get_db),
) -> SubscriptionRepository:
    """Dependency that yields a SubscriptionRepository bound to the current DB session."""
    return SubscriptionRepository(session)


def get_subscription_service(
    repo: SubscriptionRepository = Depends(get_subscription_repository),
) -> SubscriptionService:
    """Dependency that yields a SubscriptionService."""
    return SubscriptionService(repo)
