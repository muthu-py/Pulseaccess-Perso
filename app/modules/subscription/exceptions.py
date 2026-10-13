from fastapi import HTTPException, status


class SubscriptionNotFoundError(HTTPException):
    def __init__(self, detail: str = "Subscription not found") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class SubscriptionAlreadyCancelledError(HTTPException):
    def __init__(self, detail: str = "Subscription is already cancelled") -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
