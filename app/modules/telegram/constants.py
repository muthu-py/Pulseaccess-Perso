"""Telegram module constants.

Business-level configuration defaults and magic values.
"""

# Connection code settings
CONNECTION_CODE_LENGTH = 8
CONNECTION_CODE_EXPIRY_MINUTES = 15

# Deep link prefix for Telegram account linking
DEEP_LINK_PREFIX = "link_"

# Invite link defaults
INVITE_LINK_EXPIRE_SECONDS = 3600  # 1 hour
INVITE_LINK_MEMBER_LIMIT = 1  # single-use whenever supported
