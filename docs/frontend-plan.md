# PulseAccess frontend: plan and progress

Handoff notes for continuing the frontend in a new chat. Read this first, then
`web/README.md`.

_Last updated: 2026-10-14 · branch `communities`_

---

## 1. Ground rules (agreed)

- **Build UI only for features the backend already has.** Anything not built yet
  (section 4) is left out of the UI, not mocked or faked.
- **The UI is a separate app** in `web/`, with its own tests. It's built and
  tested independently of the backend tests.
- **Step by step.** Finish one step (code + tests + typecheck + lint + build),
  report, then wait for "go" before the next.
- **Commits and pushes are made as the user** (`Naveensivam03
  <naveensivam14@gmail.com>`) with **no Claude co-author line or mention**.
  Never commit `otp_dump.txt` (local login codes). Commit only when asked.
- **No fake content:** no invented stats, testimonials, customer logos or
  "trusted by" claims. Every visual shows a real product state.
- **Status is always from the backend.** Never show "Connected" or "Paid"
  because a button was clicked; poll the real status.
- Colour is never the only signal: every status has a text label and an icon.

## 2. Design direction (from the HeyClicky vs Notion analysis)

- Notion's structure and consistency + HeyClicky's real product demos, in a plain,
  trustworthy voice. Avoid generic SaaS copy ("seamless", "unlock", "supercharge").
- One design system shared by the public site and the app; different layouts.
- **Tokens** (`web/src/app/globals.css`), light + dark (OS-driven, or
  `data-theme` on `<html>`):
  - canvas `#F8F8F6`, ink `#191B22`, accent `#4568E8` (single variable, easy to
    change; user hasn't confirmed it yet)
  - semantic: success, warning, danger, info, neutral (+ `-soft` backgrounds)
  - radii: `--radius-control` 6px, `--radius-card` 12px
  - spacing scale 4/8/12/16/24/32/48/64/96; borders over shadows
- **Type:** Geist Sans everywhere, Geist Mono for IDs (chat IDs, payment IDs).
  Display 48–56px, section 36px, card 20px, body 16px, labels 13px.
- Build the **app first**, then the public site using real screenshots of it.

## 3. Tech decisions

| Area | Choice |
|---|---|
| Framework | Next.js **16.4** (App Router, TypeScript, `src/`). This version has breaking changes: read `web/node_modules/next/dist/docs/` before using an API. `cacheComponents` is on, so wrap `useSearchParams()` and other request-time reads in `<Suspense>`. |
| Styling | Tailwind v4; tokens as CSS variables mapped in `@theme inline` (classes like `bg-surface`, `text-ink-muted`, `border-line`, `bg-accent`). |
| Backend access | `next.config.ts` rewrites `/api/v1/*` → `BACKEND_URL` (default `http://localhost:8000`). Same origin, so the HttpOnly refresh cookie works and **no CORS change is needed**. |
| API types | Generated from FastAPI's OpenAPI. Repo root: `python -m scripts.export_openapi` → `web/openapi.json`; then in `web/`: `npm run gen:api` → `src/lib/api/schema.d.ts`. Friendly aliases in `src/lib/api/types.ts`. |
| Data fetching | `@tanstack/react-query` (installed, not wired yet). Use it for queries, mutations and status polling. |
| Auth | Access tokens in memory only (`session` in `client.ts`). Creator: refresh cookie → `POST /api/v1/auth/refresh` on 401 (single-flight, retry once). Member: **no refresh endpoint**, so 401 → log in again. |
| Tests | Vitest + Testing Library + jsdom (`npm test`). Playwright E2E is planned later. |

### Backend response shapes the client handles

- Success: `{ "success": true, "data": … }` → `apiRequest` returns `data`.
- Domain error: `{ "success": false, "message", "error_code" }` → `ApiError.code`.
- `HTTPException`: `{ "detail": "text" }` → `ApiError.code = "HTTP_<status>"`.
- Validation (422): `{ "detail": [{ "loc", "msg" }] }` → `ApiError.fields[field]`.
- Network failure → `ApiError.code = "NETWORK_ERROR"`.

## 4. What the backend has (UI scope)

**Usable now**

| Feature | Endpoints |
|---|---|
| Creator sign up / OTP login / refresh / logout | `POST /api/v1/auth/register` `{name, username, email, phone?}` · `POST /auth/request-otp` `{identifier}` (email or username) · `POST /auth/verify-otp` `{identifier, otp_code}` → `{access_token}` · `POST /auth/refresh` · `POST /auth/logout` |
| Creator phone | `PUT /api/v1/auth/phone` `{phone}` (with country code, e.g. `+919876543210`) |
| Creator Telegram account link | `POST /api/v1/telegram/connect/creator` → `{telegram_link, expires_at}` · `GET` same path → `{connected, telegram_username, linked_at}`. Errors: `PHONE_REQUIRED`, already connected. |
| Communities | `POST /api/v1/communities` `{name, description?}` (needs creator Telegram connected → else `TELEGRAM_NOT_CONNECTED`; one unlinked community at a time → else `PENDING_TELEGRAM_CONNECTION`) · `GET /communities/active` / `/inactive` (paginated) · `GET/PATCH /communities/{id}` · `PATCH /communities/{id}/activate` / `/deactivate` |
| Group connection status | `GET /api/v1/telegram/communities/{id}/status` → `{status, telegram_chat_id, connected_at}`; status ∈ `NOT_CONNECTED`, `CONNECTED`, `NEEDS_ATTENTION` (also legacy `CONNECTING`, `DISCONNECTED`). There is **no connect call**: the creator adds `@<bot>` to the group as admin with "Invite users via link" + "Ban users"; the backend detects it via the Telegram webhook. The UI shows instructions and **polls** this endpoint. |
| Plans (creator) | `POST /api/v1/communities/{id}/plans` `{name, description?, price (rupees string, ≥1, 2 dp), duration_days}` (community must be CONNECTED → else `COMMUNITY_NOT_CONNECTED`; `DUPLICATE_PLAN_NAME`) · `GET` same path (all plans) · `PATCH /api/v1/plans/{id}` (partial) · `PATCH /plans/{id}/activate` / `/deactivate`. Response has `price_paise` and `price` ("499.00"). |
| Member sign up / OTP login | `POST /api/v1/members/register` `{name, email, phone}` · `POST /members/request-otp` `{email}` · `POST /members/verify-otp` `{email, otp_code}` → `{access_token}` · `GET /members/me` |
| Member Telegram link | `POST/GET /api/v1/telegram/connect/member` (same as creator). Phone shared in Telegram must match the member's phone. |
| Member plans + paying | `GET /api/v1/communities/{id}/plans/available` (member token; active plans of a CONNECTED community) · `POST /api/v1/plans/{plan_id}/payment-link` (member must have Telegram connected) → `{id, payment_link_url, amount_paise, status, expires_at}`; reuses an open link · `GET /api/v1/payments/{id}` → status `created` / `paid` / `expired` / `cancelled`. Errors: `PLAN_UNAVAILABLE`, `PLAN_NOT_FOUND`, 502 if Razorpay fails. |
| Subscriptions | Activated by the Razorpay webhook. `GET /api/v1/subscriptions/member/{member_id}` exists but has **no auth** (see below). |

**Not built (leave out of the UI for now)**

- Dashboard stats / renewals: `/api/v1/dashboard/*` returns hardcoded data.
- Creator's member/subscriber list: `GET /communities/{id}/members` returns `[]`.
- Adding a paying member to the Telegram group, removal on expiry
  (draft: `member-join-design.md`, owned by a teammate).
- PulseAccess's own pricing for creators (no business model yet), so no `/pricing` page.
- Public (no-login) community page: plans need a member login today.
- Member refresh tokens; NEEDS_ATTENTION reason details (missing permissions
  aren't returned by the status endpoint yet).

## 5. Steps

### ✅ Step 1: Foundation (done)

- Scaffolded `web/` (Next 16.4, React 19.3, Tailwind v4, ESLint); `@types/node` ^24.
- `next.config.ts`: `/api/v1/*` proxy to FastAPI.
- `scripts/export_openapi.py` (repo root) + `npm run gen:api`.
- `src/lib/api/client.ts` (`apiRequest`, `ApiError`, `session`,
  `refreshCreatorSession`), `src/lib/api/types.ts`.
- `src/lib/status.ts`: backend values → `{label, tone, icon}` for
  `connection` / `payment` / `subscription`.
- Components in `src/components/ui/`: `Button` (variants, sizes, `loading`),
  `TextField` (label/hint/error wired with aria, `prefix`), `StatusBadge`,
  `Alert`, `Spinner`, `icons`.
- `/ui` page: UI kit (noindex). `/` is a placeholder.
- 27 tests (client, status mapping, components); typecheck, lint, build pass.
  Verified the proxy against the running backend.
- **Not committed yet.**

### ✅ Step 2: Creator sign-in and app shell (done, not committed)

Built as specified below. Tests need Node ≥ 22.22 (jsdom 30); `.gitignore` now un-ignores `web/src/lib/`.

- `/signup`: name, username (letters/digits/underscore, ≥3), email, phone
  (optional, with country code) → `POST /auth/register`, then go to login.
- `/login`: identifier (email or username) → `POST /auth/request-otp` → 6-digit
  code → `POST /auth/verify-otp` → store token → `/app`.
  Show the generic "If an account exists, a code has been sent" message
  (backend is anti-enumeration). Map errors: invalid / expired OTP, too many
  attempts, rate limit.
- Session restore on reload via `refreshCreatorSession()`; logout via
  `POST /auth/logout` + clear token.
- `/app` layout: sidebar (Communities, Settings) + header; redirect to `/login`
  when there's no session. Pages under `/app` are `noindex`.
- Wire React Query provider.
- Tests: form validation and error mapping, OTP step, redirect when logged out.

### Step 3: Creator onboarding

- `/app/onboarding`: (1) add phone (`PUT /auth/phone`), (2) connect Telegram
  account (`POST /telegram/connect/creator`, open link, poll `GET` until
  `connected`), (3) create first community. Skip steps already done.
- Redirect new creators here until Telegram is connected (community creation
  requires it).

### Step 4: Communities

- `/app/communities`: Active / Inactive tabs (paginated), each row with name,
  description and connection `StatusBadge`; "New community" form
  (name, description). Explain `PENDING_TELEGRAM_CONNECTION` inline.
- Edit name/description; activate/deactivate with a confirm dialog.

### Step 5: Group connection panel

- On `/app/communities/[id]`: a step list driven by the real status.
  - NOT_CONNECTED: instructions (add `@<TELEGRAM_BOT_USERNAME>` to the group,
    make it admin with "Invite users via link" + "Ban users"; must be done from
    the creator's linked Telegram account). Poll status every few seconds.
  - CONNECTED: chat ID (mono) and connected date.
  - NEEDS_ATTENTION: what to fix (admin rights, or re-add the bot).
- Bot username: from config/env (`NEXT_PUBLIC_TELEGRAM_BOT_USERNAME`).

### Step 6: Plans

- On the community page: plans table (name, price, duration, active), create
  and edit forms (price in rupees with `₹` prefix, duration in days),
  activate/deactivate. Disabled with an explanation until the community is
  CONNECTED.

### Step 7: Member flow

- `/m/signup`, `/m/login` (email OTP), `/m/connect-telegram` (phone must match).
- `/c/[communityId]`: available plans (member login required for now) →
  "Pay" → `POST /plans/{id}/payment-link` → open Razorpay link →
  `/m/payments/[id]` polls until `paid` / `expired` / `cancelled`.
- `/m/subscriptions` using `/members/me` → `/subscriptions/member/{id}`
  (works today, but that endpoint needs auth added on the backend).
- Member 401 → back to `/m/login` (no refresh yet).

### Step 8: Public site

- `/`, `/how-it-works`, `/telegram-bot` (permissions explained), `/faq`,
  `/privacy`, `/terms`, `/contact`, with real screenshots from steps 3–7.
- SEO: unique titles/descriptions, sitemap, robots, `noindex` on `/app`, `/m`, `/ui`.

### Step 9: Accessibility, mobile and E2E

- Keyboard, focus, contrast, reduced motion, ~400px widths.
- Playwright E2E for the creator and member flows.

### Later (when the backend has them)

Subscribers table, real dashboard stats, "Join group" state, public community
page, member refresh, NEEDS_ATTENTION reasons.

## 6. Running and testing

```bash
# backend (repo root)
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --port 8000 --reload
# frontend
cd web && npm install && npm run dev      # http://localhost:3000, UI kit at /ui
npm test && npm run typecheck && npm run lint && npm run build
```

Live Telegram/Razorpay testing needs ngrok (`ngrok http 8000`), then
`python -m scripts.telegram_webhook set <https-url>` and the Razorpay test-mode
webhook at `<https-url>/api/v1/webhooks/razorpay` (events `payment_link.paid`,
`payment_link.expired`, `payment_link.cancelled`; secret =
`RAZORPAY_WEBHOOK_SECRET`). OTP codes in development are written to
`otp_dump.txt`.

## 7. Open decisions

1. Accent colour: keep `#4568E8` or try alternatives after seeing `/ui`.
2. Public community page (`/c/[id]` without login) needs a backend endpoint;
   is it okay for anyone with the link to see a community's name and plans?
