"""FastAPI dependencies for payment repository, client, and service injection."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.infrastructure.database.session import get_db
from app.infrastructure.razorpay.razorpay_driver import RazorpayDriver
from app.infrastructure.razorpay.razorpay_interface import RazorpayClient
from app.modules.payment.repositories import PaymentRepository
from app.modules.payment.services import PaymentService
from app.modules.subscription.dependencies import get_subscription_service
from app.modules.subscription.services import SubscriptionService


def get_payment_repository(
    session: AsyncSession = Depends(get_db),
) -> PaymentRepository:
    """Dependency providing PaymentRepository bound to current DB session."""
    return PaymentRepository(session)


def get_razorpay_client(
    settings: Settings = Depends(get_settings),
) -> RazorpayClient:
    """Dependency providing production RazorpayDriver."""
    return RazorpayDriver(settings=settings)


def get_payment_service(
    repository: PaymentRepository = Depends(get_payment_repository),
    razorpay_client: RazorpayClient = Depends(get_razorpay_client),
    settings: Settings = Depends(get_settings),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
) -> PaymentService:
    """Dependency providing PaymentService."""
    return PaymentService(
        repository=repository,
        razorpay_client=razorpay_client,
        settings=settings,
        subscription_service=subscription_service,
    )
