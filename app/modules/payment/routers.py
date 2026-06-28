from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

@router.post("/razorpay")
async def razorpay_webhook():
    return {"status": "received"}
