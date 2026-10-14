"""Telegram module constants.

Business-level configuration defaults and magic values.
"""

# Webhook — one URL per bot, registered via setWebhook
# (update types: infrastructure telegram_constants.WEBHOOK_ALLOWED_UPDATES)
WEBHOOK_PATH = "/api/v1/webhooks/telegram"

# Deep link prefix for Telegram account linking
DEEP_LINK_PREFIX = "link_"


# Group connection (bot added to a creator's Telegram group/channel)
GROUP_CHAT_TYPES = ("group", "supergroup", "channel")
BOT_PRESENT_STATUSES = ("member", "administrator", "restricted")
BOT_GONE_STATUSES = ("left", "kicked")

# Private messages the bot sends the creator about the connection
MSG_GROUP_CONNECTED = "✅ “{title}” is now connected to your community “{community}”."
MSG_GROUP_NEEDS_ADMIN = (
    "⚠️ I was added to “{title}” for your community “{community}”, but I need to be "
    "an administrator with these permissions:\n"
    "• Invite users via link\n"
    "• Ban users\n"
    "Promote me and the connection completes automatically."
)
MSG_GROUP_NO_PENDING = (
    "I was added to “{title}”, but you have no PulseAccess community waiting for a "
    "Telegram group. Create the community first, then remove and re-add me."
)
MSG_GROUP_BOT_REMOVED = (
    "⚠️ I was removed from “{title}”. Your community “{community}” can't manage "
    "members until you add me back as an administrator."
)

# Members joining a community's group
JOIN_LINK_NAME = "PulseAccess members"
MEMBER_PRESENT_STATUSES = ("member", "administrator", "creator", "restricted")
MEMBER_GONE_STATUSES = ("left", "kicked")
JOIN_BUTTON_TEXT = "Join group"

MSG_PAID_JOIN = (
    "✅ Payment received for “{community}”.\n"
    "Tap the button below, then “Request to join”. I'll let you in right away."
)
MSG_PAID_ALREADY_IN = "✅ Payment received. Your access to “{community}” has been extended."
MSG_JOIN_DECLINED = (
    "I couldn't let you into “{community}” because this Telegram account has no "
    "active plan for it. Buy or renew a plan on the PulseAccess site, then tap the "
    "join link again."
)
