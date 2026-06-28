from pydantic import BaseModel

class CreatorRegistered(BaseModel):
    creator_id: str

class CommunityCreated(BaseModel):
    community_id: str

class PlanCreated(BaseModel):
    plan_id: str

class PaymentCaptured(BaseModel):
    payment_id: str

class SubscriptionCreated(BaseModel):
    subscription_id: str

class SubscriptionExtended(BaseModel):
    subscription_id: str

class SubscriptionExpired(BaseModel):
    subscription_id: str

class AccessGranted(BaseModel):
    member_id: str

class AccessRevoked(BaseModel):
    member_id: str

class ReminderSent(BaseModel):
    member_id: str
