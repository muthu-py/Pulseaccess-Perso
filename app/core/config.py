from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    APP_NAME: str = "PulseAccess"
    APP_ENV: str = "development"
    APP_DEBUG: bool = False

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    DATABASE_URL: str

    # ------------------------------------------------------------------
    # JWT
    # ------------------------------------------------------------------
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ------------------------------------------------------------------
    # OTP
    # ------------------------------------------------------------------
    OTP_LENGTH: int = 6
    OTP_EXPIRY_MINUTES: int = 5
    OTP_MAX_ATTEMPTS: int = 5
    OTP_REQUEST_LIMIT: int = 5
    OTP_REQUEST_WINDOW_MINUTES: int = 15
    OTP_HASH_SECRET: str

    # ------------------------------------------------------------------
    # Refresh Cookie
    # ------------------------------------------------------------------
    COOKIE_NAME: str = "refresh_token"
    COOKIE_DOMAIN: str = "localhost"
    COOKIE_PATH: str = "/"
    COOKIE_SECURE: bool = False
    COOKIE_HTTPONLY: bool = True
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"

    # ------------------------------------------------------------------
    # Email / SMTP
    # ------------------------------------------------------------------
    EMAIL_PROVIDER: str = "smtp"
    EMAIL_FROM: str = "noreply@pulseaccess.local"
    EMAIL_FROM_NAME: str = "PulseAccess"

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True

    # ------------------------------------------------------------------
    # Telegram Integration
    # ------------------------------------------------------------------
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_BOT_USERNAME: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""
    TELEGRAM_API_BASE_URL: str = "https://api.telegram.org"
    # Public base URL Telegram posts updates to (e.g. an ngrok https URL)
    TELEGRAM_WEBHOOK_BASE_URL: str = ""
    # When true, TelegramStub replaces the real driver (no Bot API calls)
    TELEGRAM_USE_STUB: bool = False

    # Retry configuration
    TELEGRAM_MAX_RETRIES: int = 5
    TELEGRAM_RETRY_BACKOFF: str = "1m,5m,15m,30m,60m"
    TELEGRAM_PROCESSING_TIMEOUT: int = 300  # seconds

    # HTTP timeouts (seconds)
    TELEGRAM_HTTP_TIMEOUT: int = 30
    TELEGRAM_CONNECT_TIMEOUT: int = 10
    TELEGRAM_READ_TIMEOUT: int = 30

    # Worker toggles
    TELEGRAM_RETRY_ENABLED: bool = True
    TELEGRAM_SYNC_ENABLED: bool = True
    TELEGRAM_HEALTH_ENABLED: bool = True

    # ------------------------------------------------------------------
    # Razorpay Integration
    # ------------------------------------------------------------------
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    RAZORPAY_API_BASE_URL: str = "https://api.razorpay.com/v1"
    # Payment links expire after this long (Razorpay minimum: 15 minutes)
    RAZORPAY_PAYMENT_LINK_EXPIRY_MINUTES: int = 30
    # Optional page Razorpay redirects the member to after paying
    RAZORPAY_PAYMENT_CALLBACK_URL: str = ""

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    LOG_LEVEL: str = "INFO"

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------
    @property
    def async_database_url(self) -> str:
        """Return an asyncpg-compatible database URL."""
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


@lru_cache
def get_settings() -> Settings:
    """Cached singleton for application settings."""
    return Settings()
