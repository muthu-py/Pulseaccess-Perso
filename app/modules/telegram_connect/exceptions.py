"""Telegram connect business exceptions."""

from app.core.exceptions import PulseAccessException


class TelegramNotConnectedError(PulseAccessException):
    status_code = 403
    error_code = "TELEGRAM_NOT_CONNECTED"
    message = "Connect your Telegram account first."


class TelegramAlreadyConnectedError(PulseAccessException):
    status_code = 409
    error_code = "TELEGRAM_ALREADY_CONNECTED"
    message = "This account is already connected to Telegram."


class PhoneRequiredError(PulseAccessException):
    status_code = 400
    error_code = "PHONE_REQUIRED"
    message = "Add a phone number to your account before connecting Telegram."
