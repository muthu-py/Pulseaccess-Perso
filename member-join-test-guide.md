# Manual test: members joining the Telegram group

## What changed
- **Join link.** Each community gets one shared Telegram join-request link, created the first time it's needed. Tapping it sends a join request; the bot approves it only if that Telegram account belongs to a member with an active plan in this community. Everyone else is declined and gets a DM explaining why.
- **After payment.** When Razorpay confirms a payment, the bot DMs the member "Payment received…" with a **Join group** button. If they're already in the group, the bot says their access was extended instead.
- **Site button.** `POST /api/v1/telegram/communities/{community_id}/invite` (member token) returns the same join link. It now requires an active plan in that community (403 `SUBSCRIPTION_INACTIVE` otherwise).
- **Group tracking.** `community_members.status` is now `PAID_NOT_JOINED` → `JOINED` → `LEFT` / `REMOVED`.
- **Expiry.** Every 5 minutes, subscriptions past `ends_at` are marked `expired`. Each one is then handled once: the member is removed from the group (ban then unban) unless another of their plans in that community is still active.
- **Subscriptions API locked down.** Create, extend and cancel are gone. Members get `GET /api/v1/subscriptions/me` and `GET /api/v1/subscriptions/{id}` (own rows only).

## 0. Setup
1. `alembic upgrade head` → head is `d9e4b7c2a615`. Subscriptions that had already ended are marked as handled, so nobody is removed by surprise.
2. Restart uvicorn.
3. Check the webhook still lists `chat_join_request` and `chat_member`: `python -m scripts.telegram_webhook info`. If not, run `set` again.
4. The bot must still be an admin with **Invite users via link** and **Ban users**.

## A. Join with your existing subscription
1. Log in as the member and Authorize with the member token.
2. `GET /api/v1/subscriptions/me` should show your active subscription.
3. `POST /api/v1/telegram/communities/{community_id}/invite` with no body. You should get an `invite_link` like `https://t.me/+…`.
4. Open the link **in the Telegram account you connected as a member**. Telegram shows **Request to join**; tap it.
5. The bot approves you straight away and you're in the group.
6. Verify in SQL:
   ```sql
   SELECT status, group_joined_at FROM community_members;
   SELECT telegram_join_link FROM communities;
   ```
   Expect `JOINED` and the link saved.

## B. Someone without a plan
Open the same link from a Telegram account that isn't a PulseAccess member (or a member with no plan here). The request is declined and the bot DMs: "I couldn't let you into … no active plan…".

## C. Pay → DM with the button
1. Leave the group (or use a second member who isn't in it).
2. Buy a plan (`POST /api/v1/plans/{plan_id}/payment-link`) and pay with `success@razorpay`.
3. The bot DMs "✅ Payment received…" with a **Join group** button. Tap it, then **Request to join** → approved.

## D. Expiry (optional, uses SQL to fast-forward)
1. Make your subscription end now:
   ```sql
   UPDATE subscriptions SET ends_at = now() - interval '1 minute' WHERE status = 'active';
   ```
2. Within 5 minutes (or restart uvicorn to run it now) the expiry worker marks it `expired` and queues a removal; the retry worker then removes you from the group (within about a minute).
3. Verify: `community_members.status` is `REMOVED`, `subscriptions.access_revoked_at` is set, and `telegram_operations` has one `REMOVE_MEMBER` row that is `COMPLETED`.
4. Pay again → you get the DM with the button and can rejoin.

## E. Subscriptions API
- `POST /api/v1/subscriptions` → 404 (no longer exists).
- `GET /api/v1/subscriptions/{id}` with another member's token → 404.
