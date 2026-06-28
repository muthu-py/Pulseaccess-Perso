from pydantic import BaseModel

class DashboardStatsResponse(BaseModel):
    total_members: int
    active_subscriptions: int

class UpcomingRenewalsResponse(BaseModel):
    renewals: list
