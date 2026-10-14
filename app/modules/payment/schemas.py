"""Payment schemas for order creation and response serialization."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PaymentOrderResponse(BaseModel):
    """Response returned to client containing Razorpay order details for checkout."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    razorpay_order_id: str | None = None
    member_id: uuid.UUID
    plan_id: uuid.UUID
    amount_paise: int
    currency: str
    status: str
    receipt_id: str | None = None
    key_id: str | None = None
    created_at: datetime


class PaymentLinkResponse(BaseModel):
    """A member's purchase attempt and the Razorpay link to pay it."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    plan_id: uuid.UUID
    community_id: uuid.UUID | None = None
    amount_paise: int
    currency: str
    status: str
    payment_link_url: str | None = None
    expires_at: datetime | None = None
    paid_at: datetime | None = None
    created_at: datetime
