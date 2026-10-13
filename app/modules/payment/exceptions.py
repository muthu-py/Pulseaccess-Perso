"""Exceptions for payment module."""

from fastapi import HTTPException, status


class PlanNotFoundError(HTTPException):
    def __init__(self, detail: str = "Plan not found") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class PaymentOrderNotFoundError(HTTPException):
    def __init__(self, detail: str = "Payment order not found") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class PaymentOrderCreationError(HTTPException):
    def __init__(self, detail: str = "Failed to create payment order with payment gateway") -> None:
        super().__init__(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)
