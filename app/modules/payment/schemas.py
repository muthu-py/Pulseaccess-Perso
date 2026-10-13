"""Payment schemas for order creation and response serialization."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CreatePaymentOrderRequest(BaseModel):
    """Request payload to create a new checkout order."""

    member_id: uuid.UUID
    plan_id: uuid.UUID


class PaymentOrderResponse(BaseModel):
    """Response returned to client containing Razorpay order details for checkout."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    razorpay_order_id: str
    member_id: uuid.UUID
    plan_id: uuid.UUID
    amount_paise: int
    currency: str
    status: str
    receipt_id: str | None = None
    key_id: str | None = None
    created_at: datetime
