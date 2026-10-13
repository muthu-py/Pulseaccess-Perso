"""Exceptions for Razorpay infrastructure client."""


class RazorpayAPIError(Exception):
    """Raised when Razorpay API returns an error or fails."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class RazorpaySignatureVerificationError(Exception):
    """Raised when Razorpay webhook signature verification fails."""

    def __init__(self, message: str = "Invalid Razorpay signature") -> None:
        super().__init__(message)
        self.message = message
