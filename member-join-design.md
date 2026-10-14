# Adding members to a community group: plan (discussion draft, not implemented)

## What already exists
- The member registers, logs in and connects Telegram. Their Telegram ID is in `telegram_accounts`.
- `POST /api/v1/payments/orders` → Razorpay → webhook → `activate_or_renew` creates an ACTIVE subscription (`payment/services.py`).
- `community_members` table exists (member_id, community_id, status, joined_at) but nothing writes to it yet.
- `POST /api/v1/telegram/communities/{id}/invite` makes a one-person invite link, but **skips the subscription check** (`telegram/services.py`, comment instead of a check).
- The bot is admin in the group with **Invite Users via Link** (needed to approve join requests) and **Ban Users** (needed to remove).

## Gaps found while planning
1. **The creator's group never gets linked.** Nothing saves `communities.telegram_chat_id` when the bot is added to a group, so no group exists to invite members into. This blocks everything below.
2. **Nothing marks a subscription EXPIRED.** `ends_at` passes but status stays ACTIVE, so no one is ever removed.
3. **The expiry worker re-queues the same removal every 5 minutes** for every expired subscription, forever.
4. **The expiry worker ignores other plans.** A member with two plans in one community would be removed when one plan ends.

## Proposed flow

### Step 0: creator links the group (prerequisite)
- The creator's community page shows "Connect group", a link `t.me/<bot>?startgroup=<token>`.
- The creator picks the group. Telegram sends `my_chat_member` with `from.id` = the creator's Telegram ID.
- The server checks the token belongs to that creator's community and that `from.id` is that creator's connected Telegram account, then saves `telegram_chat_id` and marks the community CONNECTED.
- The server creates **one join-request link** for the group (`createChatInviteLink` with `creates_join_request=true`) and stores it on the community.

### Step 1: member pays
- Plans can only be bought for a community whose group is CONNECTED.
- After the payment webhook activates the subscription, the server upserts `community_members` with status **PAID_NOT_JOINED**.

### Step 2: member gets the link
- The bot DMs the member: "Payment received for <community>. Tap to join." with a **Join group** button (the community's join-request link). The bot can DM them because they already started it when connecting.
- The site also shows a **Join group** button (the invite endpoint, now with a real subscription check).

### Step 3: member taps the link
- Telegram shows "Request to join". The member taps it. The bot gets `chat_join_request` with the group's chat ID and the member's Telegram ID.
- The server finds the community by chat ID and the member by Telegram ID, then checks for any ACTIVE subscription to any plan in that community.
  - Yes → `approveChatJoinRequest`, `community_members` status **JOINED**, `joined_at` set.
  - No → `declineChatJoinRequest`, and the bot DMs "You need an active plan for <community>. Subscribe at <site>."
- The link is shared, but that is safe: a stranger who gets it can only *request*, and the bot declines them.

### Step 4: staying in sync
- `chat_member` update says the member left the group → status **LEFT**. The subscription is untouched, so they can request again.
- Member is already in the group when they pay (joined earlier) → on activation, `getChatMember` checks and sets JOINED directly.

### Step 5: expiry and renewal
- A job marks subscriptions EXPIRED once `ends_at` has passed.
- For each newly expired subscription, if the member has **no other ACTIVE subscription in that community**, queue one REMOVE_MEMBER (ban then unban, so they can come back later) and set status **REMOVED**.
- Each subscription is handled once (e.g. a `revoked_at` column) so removals aren't re-queued.
- Renewing before expiry: nothing changes in the group. Renewing after removal: same as a new payment, they get the link again.

## Data changes
- `communities`: add `telegram_join_link`.
- `community_members.status`: PAID_NOT_JOINED, JOINED, LEFT, REMOVED.
- `subscriptions`: add `revoked_at`; foreign keys to members and plans.
- `telegram_link_tokens` (or a similar table) reused for the group-connect token, with owner = creator and a community_id.

## New Telegram calls
`createChatInviteLink` (creates_join_request), `approveChatJoinRequest`, `declineChatJoinRequest`, `getChatMember`, `banChatMember`, `unbanChatMember` (only_if_banned).

## Decisions needed
1. **Invite link:** one shared join-request link per community (recommended) or a new single-use link per member?
2. **Delivery:** bot DM after payment plus a site button (recommended) or site button only?
3. **Grace period after expiry:** remove right away (recommended) or wait N days?
4. **Selling plans before the group is linked:** block it (recommended) or allow it?
5. **Scope:** include the creator group-linking fix in this phase (recommended, since nothing works without it)?
6. **Strangers requesting to join:** decline and DM a "subscribe on the site" message (recommended) or decline silently?
7. **People already in the group without a subscription** (for example, added by the creator by hand): leave them alone (recommended) or remove them?
