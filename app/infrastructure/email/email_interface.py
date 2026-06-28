from typing import Protocol


class EmailService(Protocol):
    """Interface for sending transactional emails."""

    async def send_login_otp(
        self,
        to_email: str,
        otp_code: str,
        creator_name: str,
    ) -> None:
        """Send an OTP login code to the given email address."""
        ...
