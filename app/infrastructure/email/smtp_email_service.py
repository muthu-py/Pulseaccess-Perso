import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import aiosmtplib

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"


class SMTPEmailService:
    """SMTP-based implementation of EmailService."""

    def __init__(self, settings: Settings) -> None:
        self._host = settings.SMTP_HOST
        self._port = settings.SMTP_PORT
        self._username = settings.SMTP_USERNAME
        self._password = settings.SMTP_PASSWORD
        self._use_tls = settings.SMTP_USE_TLS
        self._from_email = settings.EMAIL_FROM
        self._from_name = settings.EMAIL_FROM_NAME
        self._is_dev = settings.is_development

    def _load_template(self, template_name: str) -> str:
        """Load an HTML email template from disk."""
        template_path = TEMPLATE_DIR / template_name
        return template_path.read_text(encoding="utf-8")

    def _build_otp_html(self, otp_code: str, creator_name: str, expiry_minutes: int) -> str:
        """Build the OTP email HTML from template."""
        html = self._load_template("otp_email_template.html")
        html = html.replace("{{otp_code}}", otp_code)
        html = html.replace("{{creator_name}}", creator_name)
        html = html.replace("{{expiry_minutes}}", str(expiry_minutes))
        return html

    async def send_login_otp(
        self,
        to_email: str,
        otp_code: str,
        creator_name: str,
    ) -> None:
        """Send the OTP login email."""
        if self._is_dev:
            logger.info(
                "DEV MODE — OTP for %s: %s (not sending real email)",
                to_email,
                otp_code,
            )
            return

        subject = f"{self._from_name} — Your Login Code"
        html_body = self._build_otp_html(
            otp_code=otp_code,
            creator_name=creator_name,
            expiry_minutes=5,
        )

        message = MIMEMultipart("alternative")
        message["From"] = f"{self._from_name} <{self._from_email}>"
        message["To"] = to_email
        message["Subject"] = subject

        # Plain-text fallback
        plain_text = (
            f"Hi {creator_name},\n\n"
            f"Your login code is: {otp_code}\n\n"
            f"This code expires in 5 minutes.\n\n"
            f"If you didn't request this, please ignore this email.\n\n"
            f"— {self._from_name}"
        )
        message.attach(MIMEText(plain_text, "plain"))
        message.attach(MIMEText(html_body, "html"))

        try:
            await aiosmtplib.send(
                message,
                hostname=self._host,
                port=self._port,
                username=self._username,
                password=self._password,
                start_tls=self._use_tls,
            )
            logger.info("OTP email sent to %s", to_email)
        except aiosmtplib.SMTPException:
            logger.exception("Failed to send OTP email to %s", to_email)
            raise
