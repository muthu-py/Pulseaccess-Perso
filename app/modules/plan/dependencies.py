"""FastAPI dependencies for the plan module."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_db
from app.modules.plan.repositories import PlanRepository
from app.modules.plan.services import PlanService


def get_plan_service(session: AsyncSession = Depends(get_db)) -> PlanService:
    return PlanService(PlanRepository(session))
