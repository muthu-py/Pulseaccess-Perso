from pydantic import BaseModel

class SubscriptionResponse(BaseModel):
    id: str
    status: str

class ExtendSubscriptionRequest(BaseModel):
    days: int
