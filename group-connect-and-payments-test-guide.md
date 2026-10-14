# Manual test: group connection and Razorpay payment links

## 0. Setup (once)
1. Run `alembic upgrade head`. The head should be `a6c8e0f24b13`, and `alembic current` should show that.
2. Add these to `.env` from Razorpay **Test Mode** (Dashboard → Account & Settings → API Keys):
   ```
   RAZORPAY_KEY_ID=rzp_test_...
   RAZORPAY_KEY_SECRET=...
   RAZORPAY_WEBHOOK_SECRET=<any long random string>
   ```
3. Restart uvicorn and start ngrok on the same port.
4. Re-register the Telegram webhook so it includes the new update types:
   `python -m scripts.telegram_webhook set https://<your-ngrok>.ngrok-free.app`
   Then `python -m scripts.telegram_webhook info` should list `my_chat_member`, `chat_member` and `chat_join_request`.
5. In Razorpay Test Mode, go to Dashboard → Webhooks → Add:
   - URL: `https://<your-ngrok>.ngrok-free.app/api/v1/webhooks/razorpay`
   - Secret: the same `RAZORPAY_WEBHOOK_SECRET`
   - Events: `payment_link.paid`, `payment_link.expired`, `payment_link.cancelled`

Whenever ngrok restarts, update both webhooks with the new URL.

## A. Connect a Telegram group (creator)
1. Log in as the creator and Authorize in /docs.
2. Call `GET /api/v1/communities/active`. If the "Test community" from earlier is listed, it's your pending one; use its `id`. Otherwise create one with `POST /api/v1/communities`.
3. Check the one-at-a-time rule: `POST /api/v1/communities` with another name should return **409 `PENDING_TELEGRAM_CONNECTION`**.
4. In Telegram, create a group. Use the **same Telegram account you connected as creator**.
5. Add the bot as a plain member first (Add members → search the bot). The bot should DM you **"⚠️ I was added to … I need to be an administrator…"**.
6. Promote the bot: group → Edit → Administrators → the bot. Turn on **Invite users via link** and **Ban users**. The bot should DM **"✅ … is now connected to your community …"**.
7. Verify:
   - `GET /api/v1/telegram/communities/{id}/status` should show `"status": "CONNECTED"` and a `telegram_chat_id` (a negative number).
   - `POST /api/v1/communities` with a second name should now succeed.
8. Optional: remove the bot from the group. You should get a DM "⚠️ I was removed…" and the status becomes `NEEDS_ATTENTION`. Add it back as admin and the status returns to CONNECTED.

## B. Create a plan (creator)
1. `POST /api/v1/communities/{id}/plans`:
   ```json
   {"name": "Monthly", "price": 1, "duration_days": 30}
   ```
2. Copy the plan `id` from the response.
   - The same request again should fail with a duplicate-name error.
   - The same request on a community that isn't CONNECTED should fail.

## C. Buy the plan (member)
1. Log in as the member (`/api/v1/members/verify-otp`) and Authorize with the member token.
2. `GET /api/v1/communities/{id}/plans/available` should list "Monthly" with `"price": "1.00"`.
3. `POST /api/v1/plans/{plan_id}/payment-link` with no body should return 201 with `payment_link_url` and `status: "created"`. Call it again and you should get the **same** `id` and URL.
4. Open `payment_link_url` and pay in test mode, for example with UPI ID `success@razorpay`.
5. Verify:
   - `GET /api/v1/payments/{id}` should show `status: "paid"` and `paid_at` set.
   - In SQL:
     ```sql
     SELECT member_id, plan_id, status, starts_at, ends_at FROM subscriptions;
     SELECT event_id, event_type, status FROM payment_events ORDER BY created_at DESC LIMIT 5;
     ```
     You should see one ACTIVE subscription ending in 30 days, and a `payment_link.paid` event with status `processed`.
6. Optional: create another link and don't pay it. After 30 minutes, `GET /api/v1/payments/{id}` shows `expired`.
7. Optional: call `POST /api/v1/plans/{plan_id}/payment-link` with the creator token. It should be rejected with 403.

## If something doesn't happen
- **No DM after adding the bot.** Check the uvicorn log for the `my_chat_member` POST. Also check that you added the bot from the Telegram account connected as creator. A bot added by anyone else is ignored on purpose.
- **Payment paid but status still `created`.**
  - The Razorpay webhook didn't arrive or was rejected. Check Razorpay → Webhooks → the webhook → recent deliveries.
  - A 400 response means a signature problem: the secret in Razorpay doesn't match `.env`.
