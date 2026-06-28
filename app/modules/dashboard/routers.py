from fastapi import APIRouter
from app.modules.dashboard.schemas import DashboardStatsResponse, UpcomingRenewalsResponse

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

@router.get("/stats", response_model=DashboardStatsResponse)
async def get_stats():
    return {"total_members": 100, "active_subscriptions": 95}

@router.get("/renewals", response_model=UpcomingRenewalsResponse)
async def get_renewals():
    return {"renewals": []}
