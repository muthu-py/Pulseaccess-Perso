"""Exceptions for payment module."""

from fastapi import HTTPException, status

from app.core.exceptions import PulseAccessException


class PlanNotFoundError(HTTPException):
    def __init__(self, detail: str = "Plan not found") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class PaymentOrderNotFoundError(HTTPException):
    def __init__(self, detail: str = "Payment order not found") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class PaymentOrderCreationError(HTTPException):
    def __init__(self, detail: str = "Failed to create payment order with payment gateway") -> None:
        super().__init__(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)


class InvalidWebhookSignatureError(HTTPException):
    def __init__(self, detail: str = "Invalid webhook signature") -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class PlanUnavailableError(PulseAccessException):
    status_code = 409
    error_code = "PLAN_UNAVAILABLE"
    message = "This plan is not available for purchase right now."


class PaymentNotFoundError(PulseAccessException):
    status_code = 404
    error_code = "PAYMENT_NOT_FOUND"
    message = "Payment not found."
