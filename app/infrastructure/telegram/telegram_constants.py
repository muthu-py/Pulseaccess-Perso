"""Telegram Bot API endpoint constants.

Centralises all Telegram REST paths so that the driver never
hard-codes URLs and business services never concatenate them (Doc 04 §13).
"""

# Bot management
GET_ME = "getMe"

# Chat operations
GET_CHAT = "getChat"
GET_CHAT_MEMBER = "getChatMember"

# Invite links
CREATE_CHAT_INVITE_LINK = "createChatInviteLink"

# Membership management
BAN_CHAT_MEMBER = "banChatMember"
UNBAN_CHAT_MEMBER = "unbanChatMember"

# Webhook management
SET_WEBHOOK = "setWebhook"
DELETE_WEBHOOK = "deleteWebhook"
GET_WEBHOOK_INFO = "getWebhookInfo"
