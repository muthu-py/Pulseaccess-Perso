# Connect Telegram: what changed and how to test it

All changes are in `C:\Users\Muthu\Downloads\PulseAccess` (48 files, nothing committed to git).
Tests: `pytest` → 29 passed (11 new in `tests/test_telegram_connect.py`). The migration was run up and down on PostgreSQL 16.

## What changed
- **New module `app/modules/telegram_connect/`**: one "Connect Telegram" flow for creators and members (tables `telegram_accounts`, `telegram_link_tokens`).
- **Members**: one account per person (name, phone, email). Register and log in with an email OTP at `/api/v1/members/...`. New `community_members` table for many-to-many (joining comes in the next step).
- **Separate logins**: access tokens now carry `role` (`creator` or `member`). Creator endpoints reject member tokens and the other way round. Old creator tokens without a role still count as creator.
- **Creators** get a phone number: `phone` on register, or `PUT /api/v1/auth/phone`.
- **Guards**:
  - `POST /api/v1/communities` needs a creator with Telegram connected.
  - `POST /api/v1/payments/orders` needs a member login with Telegram connected. The body is now just `{"plan_id": ...}`; the member comes from the token.
- **Bot**: `send_message` added. The webhook now answers `/start <code>`, asks for the phone with a "Share phone number" button, and links on a match.
- **Fixes**:
  - The webhook no longer logs your secret or full message bodies.
  - The real Telegram client is used whenever `TELEGRAM_BOT_TOKEN` is set (before, `development` always used the fake one).
  - `setWebhook` now asks for `chat_member` and `chat_join_request` updates.
- **Removed**: `POST /api/v1/telegram/link` and `GET /api/v1/telegram/link/status` (replaced by the connect endpoints below).

## New endpoints
| Who | Method | Path |
|---|---|---|
| Member | POST | `/api/v1/members/register` `{name, email, phone}` |
| Member | POST | `/api/v1/members/request-otp` `{email}` |
| Member | POST | `/api/v1/members/verify-otp` `{email, otp_code}` → access token |
| Member | GET | `/api/v1/members/me` |
| Member | POST / GET | `/api/v1/telegram/connect/member` (get link / status) |
| Creator | PUT | `/api/v1/auth/phone` `{phone}` |
| Creator | POST / GET | `/api/v1/telegram/connect/creator` (get link / status) |

Phone numbers must include the country code, e.g. `+919876543210`.

## Live test with your bot
1. In `.env`, set:
   - `TELEGRAM_BOT_TOKEN`: the token of @PulseAccess_admin_test_1_bot
   - `TELEGRAM_BOT_USERNAME=PulseAccess_admin_test_1_bot`
   - `TELEGRAM_WEBHOOK_SECRET`: any value
2. Run the migration: `alembic upgrade head`. The `members` table must be empty, which it is today.
3. Start the server and ngrok, then register the webhook again so Telegram sends the new update types:
   ```
   curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url":"https://<your-ngrok>/api/v1/webhooks/telegram","secret_token":"<SECRET>","allowed_updates":["message","my_chat_member","chat_member","chat_join_request"]}'
   ```
4. Register a member with **the same phone number your Telegram account uses**, then log in:
   - `POST /members/register`
   - `POST /members/request-otp`. In development the code is written to `otp_dump.txt`.
   - `POST /members/verify-otp` → copy `access_token`.
5. Call `POST /api/v1/telegram/connect/member` with `Authorization: Bearer <token>`, then open `telegram_link` on your phone.
6. In Telegram: tap **Start**, then **Share phone number**. The bot should reply "Connected!".
7. `GET /api/v1/telegram/connect/member` should show `connected: true`.

What the bot does in other cases:
- A different phone number → "doesn't match".
- A forwarded contact → "share your own".
- A link that is expired, used, or opened by another Telegram account → "expired or was already used".

## Not done yet (next steps)
- Adding members to the group: join-request approval, the subscription check on invites, and the `community_members` join flow.
- Creator group auto-linking (the bot sees who added it).
- Member refresh tokens: member logins last `ACCESS_TOKEN_EXPIRE_MINUTES` (15 min) for now.
- `POST /api/v1/subscriptions` and `GET /api/v1/payments/orders/{id}` still have no auth (unchanged from before).
