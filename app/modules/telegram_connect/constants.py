"""Telegram connect constants."""

# One-time code behind the "Connect Telegram" button
LINK_TOKEN_BYTES = 24  # token_urlsafe(24) → 32 chars, under Telegram's 64-char start limit
LINK_TOKEN_EXPIRY_MINUTES = 15

SHARE_PHONE_BUTTON = "Share phone number"

MSG_SHARE_PHONE = (
    "To connect your PulseAccess account, tap \"Share phone number\" below."
)
MSG_OPEN_FROM_SITE = (
    "Hi! To connect your PulseAccess account, use the \"Connect Telegram\" "
    "button on the PulseAccess site."
)
MSG_LINK_EXPIRED = (
    "This link has expired or was already used. Please tap \"Connect Telegram\" "
    "on the PulseAccess site again."
)
MSG_NOT_OWN_CONTACT = "Please share your own phone number using the button below."
MSG_PHONE_MISMATCH = (
    "This Telegram account's phone number doesn't match the one on your "
    "PulseAccess account. Update your phone number on the site, then try again."
)
MSG_ALREADY_USED = (
    "This Telegram account is already connected to another PulseAccess account."
)
MSG_CONNECTED = "Connected! You can go back to the PulseAccess site now."
