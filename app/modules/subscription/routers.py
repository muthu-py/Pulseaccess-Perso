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
