# PulseAccess: API Endpoint Inventory and UI/UX Design Prompt

PulseAccess lets **creators** sell paid access to a Telegram group. **Members** sign up, link Telegram, pay through Razorpay, and are let into the group by a bot. When a plan expires, the member is removed.

- Backend: FastAPI, all routes under `/api/v1`. Source: `app/modules/*/routers.py`.
- Frontend: Next.js 16 / React 19 / Tailwind v4 in `web/`. It proxies `/api/v1/*` to the backend through `next.config.ts` rewrites.
- Generated API types: `web/src/lib/api/schema.d.ts`. Fetch wrapper: `web/src/lib/api/client.ts`.

Legend for the **Frontend status** column:

- ✅ wired in the UI today
- 🟡 backend exists, no UI yet (opportunity)
- ⛔ stub or internal, do not build UI

## 1. Conventions

| Item | Value |
|---|---|
| Success envelope | `{ "success": true, "data": … }` |
| Domain error | `{ "success": false, "message", "error_code" }` |
| HTTP error | `{ "detail": "text" }` |
| Validation (422) | `{ "detail": [{ "loc", "msg" }] }`, map to per-field errors |
| Creator auth | Access token in memory. HttpOnly refresh cookie, on 401 call `POST /auth/refresh` once, then retry. |
| Member auth | Access token in memory. **No refresh endpoint**, so on 401 send the member to `/m/login`. |
| IDs | UUIDs. Show Telegram chat IDs and payment IDs in a mono font. |
| Money | Backend stores paise (`price_paise`) and also returns `price` ("499.00"). Display ₹. |

## 2. Endpoints by role

### 2.1 Creator authentication

| Endpoint | Auth | Purpose | When it is called | UI location |
|---|---|---|---|---|
| `POST /auth/register` `{name, username, email, phone?}` | none | Create creator account | Submit of the signup form. After success, immediately request an OTP. | ✅ `/signup` |
| `POST /auth/request-otp` `{identifier}` (email or username) | none | Email a 6-digit login code. Anti-enumeration: always returns the generic "If an account exists…" message. | Login step 1, resend code, auto-sent after signup | ✅ `/login` step 1 |
| `POST /auth/verify-otp` `{identifier, otp_code}` → `{access_token}` | none | Exchange the code for a session. Sets the refresh cookie. | Login step 2 | ✅ `/login` step 2 |
| `POST /auth/refresh` | refresh cookie | Get a new access token | App load (session restore), or on any 401 | ✅ invisible. Auth provider, `/app` layout guard |
| `POST /auth/logout` | creator | Revoke the session | "Log out" in the user menu | ✅ `/app` shell header/sidebar |
| `GET /auth/me` | creator | Current creator profile (name, email, phone, telegram state) | Account/Settings page, header avatar | 🟡 `/app/settings` could use it |
| `PUT /auth/phone` `{phone}` (with country code) | creator | Add or change phone. Required before Telegram link. | Onboarding step 1 | ✅ `/app/onboarding` step 1 |

### 2.2 Creator: Telegram account link

| Endpoint | Auth | Purpose | When | UI location |
|---|---|---|---|---|
| `POST /telegram/connect/creator` → `{telegram_link, expires_at}` | creator | Create a one-time deep link (`t.me/<bot>?start=link_…`) | User clicks "Connect Telegram". Errors: `PHONE_REQUIRED`, already connected. | ✅ `/app/onboarding` step 2 |
| `GET /telegram/connect/creator` → `{connected, telegram_username, linked_at}` | creator | Poll whether the link finished | Every ~3s after the link is opened. Also on app load to gate community creation. | ✅ onboarding step 2, `/app` gating, Settings |

### 2.3 Communities (creator)

| Endpoint | Auth | Purpose | When | UI location |
|---|---|---|---|---|
| `POST /communities` `{name, description?}` | creator | Create a community. Needs Telegram linked (`TELEGRAM_NOT_CONNECTED`). Only one unlinked community at a time (`PENDING_TELEGRAM_CONNECTION`). | "New community" submit, onboarding step 3 | ✅ `/app/communities/new`, onboarding |
| `GET /communities/active?page&page_size` | creator | Paginated active communities | Communities home, Active tab. Also count for empty-state logic. | ✅ `/app` |
| `GET /communities/inactive?page&page_size` | creator | Paginated inactive communities | Inactive tab | ✅ `/app` |
| `GET /communities/{id}` | creator | One community's details | Community detail page load | ✅ `/app/communities/[id]` |
| `PATCH /communities/{id}` `{name?, description?}` | creator | Edit | "Edit" form submit | ✅ detail page |
| `PATCH /communities/{id}/activate` | creator | Re-enable a community | "Activate" button (confirm dialog) | ✅ detail page |
| `PATCH /communities/{id}/deactivate` | creator | Hide / pause a community | "Deactivate" button (confirm dialog) | ✅ detail page |

### 2.4 Creator: Telegram group connection

There is **no "connect group" call**. The creator adds the bot to the group as admin (permissions: *Invite users via link*, *Ban users*). The backend detects this through the Telegram webhook. The UI only shows instructions and polls the status.

| Endpoint | Auth | Purpose | When | UI location |
|---|---|---|---|---|
| `GET /telegram/communities/{id}/status` → `{status, telegram_chat_id, connected_at}`. Status is `NOT_CONNECTED`, `CONNECTED`, `NEEDS_ATTENTION`, plus legacy `CONNECTING`, `DISCONNECTED`. | creator | Real connection state | Poll every few seconds while `NOT_CONNECTED`. Fetch on detail page. Drives plan-section gating. | ✅ `ConnectionPanel` on `/app/communities/[id]`, list badges |
| `DELETE /telegram/communities/{id}` (204) | creator | Disconnect the group. Business data is kept. | "Disconnect group" destructive action (confirm dialog) | 🟡 no UI yet. Add to connection panel (danger zone). |
| `DELETE /telegram/communities/{id}/members/{member_id}` → `{member_id, community_id, membership_status, telegram_removal}`. `telegram_removal` is `DONE`, `QUEUED`, `NOT_NEEDED` or `ALREADY_REMOVED`. | creator | Remove a member whose plan ended now, instead of waiting for the daily expiry job. Returns 409 while the plan is still active. | "Remove from group" on an expired member row | 🟡 no UI yet. Needs a member list. |
| `POST /webhooks/telegram` | secret header | Receives bot updates (group connect, join requests, link `/start`) | Called by Telegram only | ⛔ never from the UI |

### 2.5 Plans

| Endpoint | Auth | Purpose | When | UI location |
|---|---|---|---|---|
| `POST /communities/{id}/plans` `{name, description?, price (₹, ≥1, 2 dp), duration_days (1–3650)}` | creator | Create a plan. The community must be `CONNECTED` (`COMMUNITY_NOT_CONNECTED`). Names must be unique (`DUPLICATE_PLAN_NAME`). | "Add plan" submit | ✅ `PlansSection` on community detail |
| `GET /communities/{id}/plans` | creator | All plans (active and inactive) | Community detail load | ✅ `PlansSection` |
| `PATCH /plans/{id}` (partial) | creator | Edit a plan | "Edit plan" submit | ✅ `PlansSection` |
| `PATCH /plans/{id}/activate` · `/deactivate` | creator | Toggle availability to members | Row toggle | ✅ `PlansSection` |
| `GET /communities/{id}/plans/available` | **member** | Active plans of a CONNECTED community | Member opens the community page | ✅ `/c/[communityId]` |

### 2.6 Member authentication and profile

| Endpoint | Auth | Purpose | When | UI location |
|---|---|---|---|---|
| `POST /members/register` `{name, email, phone}` | none | Create a member account (phone must match what they share with Telegram) | Signup submit | ✅ `/m/signup` |
| `POST /members/request-otp` `{email}` | none | Email a login code | Login step 1, resend | ✅ `/m/login` |
| `POST /members/verify-otp` `{email, otp_code}` → `{access_token}` | none | Log in | Login step 2 | ✅ `/m/login` |
| `GET /members/me` → `{id, name, phone, email, is_active, telegram_connected}` | member | Session check and profile | Member portal layout load | ✅ `/m/(portal)` shell |
| `POST /telegram/connect/member` | member | Deep link to link the member's Telegram. The phone shared in Telegram must match the member's phone. | "Connect Telegram" button | ✅ `/m/connect-telegram` |
| `GET /telegram/connect/member` | member | Poll link status | Every ~3s after the link is opened. Also before allowing payment. | ✅ `/m/connect-telegram`, pay gate |

### 2.7 Payment, subscription and joining the group

| Endpoint | Auth | Purpose | When | UI location |
|---|---|---|---|---|
| `POST /plans/{plan_id}/payment-link` → `{id, payment_link_url, amount_paise, status, expires_at}` | member (Telegram connected) | Create a Razorpay payment link. Reuses an open link. Errors: `PLAN_UNAVAILABLE`, `PLAN_NOT_FOUND`, 502 if Razorpay fails. | "Pay ₹X" on a plan card. Then open `payment_link_url` and go to the payment status page. | ✅ `/c/[communityId]` → `/m/payments/[id]` |
| `GET /payments/{id}` → status `created`, `paid`, `expired` or `cancelled` | member | Poll payment result | Every ~3s on the payment status page until terminal | ✅ `/m/payments/[id]` |
| `POST /webhooks/razorpay` | HMAC signature | Razorpay → activates the subscription, triggers the bot DM with the "Join group" button | Called by Razorpay only | ⛔ never from the UI |
| `GET /subscriptions/me` → `{subscriptions[], total}`. Each has `id, plan_id, status, starts_at, ends_at, cancelled_at`. Status is `active`, `expired`, `cancelled` or `pending`. | member | List my subscriptions | Subscriptions page load | ✅ `/m/subscriptions` |
| `GET /subscriptions/{id}` | member | One subscription | Detail view or deep link | 🟡 no dedicated UI |
| `POST /telegram/communities/{id}/invite` → `{invite_link, expires_at?}` | member (active plan + Telegram linked) | Get the group join-request link. The bot approves only active members, so it is safe to show. | "Join Telegram group" button on an active subscription, and on the payment-success state | 🟡 **no UI yet**. This closes the loop after payment. |

### 2.8 Stubs and not-ready endpoints (do not design real UI for these)

| Endpoint | State | Note |
|---|---|---|
| `GET /dashboard/stats` | hardcoded `{total_members: 100, active_subscriptions: 95}` | Fake data. Do not display. |
| `GET /dashboard/renewals` | hardcoded `{renewals: []}` | Fake data. |
| `GET /communities/{id}/members` | returns `[]` | No member list yet. The creator's subscriber table is blocked on this. |
| `GET /` | `{"message": "Welcome…"}` | Health check only. |

## 3. Screen map (UI area → endpoints)

| Area | Route | Endpoints |
|---|---|---|
| Public site | `/`, `/how-it-works`, `/telegram-bot`, `/faq`, `/privacy`, `/terms`, `/contact` | none (static) |
| Creator signup / login | `/signup`, `/login` | register, request-otp, verify-otp |
| Creator shell | `/app/*` | refresh, logout, `GET /telegram/connect/creator` (gating) |
| Onboarding | `/app/onboarding` | `PUT /auth/phone`, Telegram connect creator POST+GET, `POST /communities` |
| Communities home | `/app` | communities active / inactive |
| New community | `/app/communities/new` | `POST /communities` |
| Community detail | `/app/communities/[id]` | community GET/PATCH/activate/deactivate, telegram status (poll), plans CRUD, 🟡 disconnect |
| Settings | `/app/settings` | 🟡 `GET /auth/me`, phone, Telegram link status |
| Member signup / login | `/m/signup`, `/m/login` | members register, request-otp, verify-otp |
| Member Telegram link | `/m/connect-telegram` | members/me, Telegram connect member POST+GET |
| Community plans (member) | `/c/[communityId]` | plans/available, payment-link |
| Payment status | `/m/payments/[id]` | `GET /payments/{id}` (poll), 🟡 invite |
| My subscriptions | `/m/subscriptions` | subscriptions/me, 🟡 invite, 🟡 subscriptions/{id} |

## 4. Gaps worth designing for now

1. **"Join group" after payment** (`POST /telegram/communities/{id}/invite`): primary CTA on the payment-success state and on active subscription cards.
2. **Disconnect group** (`DELETE /telegram/communities/{id}`): danger-zone action with a confirm dialog on the connection panel.
3. **Remove expired member** (`DELETE …/members/{member_id}`): design the row action, and its four result states, for when the member list endpoint lands. Show it as a "coming soon" layout only if the user asks for it.
4. **Settings page** using `GET /auth/me`.
5. **Subscriptions cards** only get `plan_id`. Plan and community names are not in the response, so the UI must either fetch them separately or the backend must add them. Flag this rather than invent data.

---

# 5. Prompt for the UI/UX design and implementation agent

Copy everything below this line into the other AI agent.

---

````text
ROLE
You are a senior product designer and front-end engineer. Redesign and implement the UI for PulseAccess, a SaaS that lets creators sell paid access to a Telegram group. Deliver working code, not mockups.

PRODUCT IN ONE PARAGRAPH
A creator signs up, links their Telegram account, creates a community, adds the PulseAccess bot as an admin of their Telegram group, and defines paid plans (price + duration). A member signs up, links their Telegram account, picks a plan, pays through a Razorpay payment link, and the bot lets them into the group. When the plan ends, the member is removed. All payment and connection status comes from the backend. The UI never fakes state.

TECH STACK (already in the repo, in /web)
- Next.js 16.4 App Router, React 19, TypeScript, Tailwind v4.
- IMPORTANT: Next 16 has breaking changes. Read web/node_modules/next/dist/docs/ before using any Next API. `cacheComponents` is on, so wrap useSearchParams() and other request-time reads in <Suspense>.
- Data fetching: @tanstack/react-query. API wrapper: web/src/lib/api/client.ts (`apiRequest`, `ApiError`, `session`). Types: web/src/lib/api/schema.d.ts and types.ts.
- Backend is proxied at same-origin /api/v1/*. Do not call the backend by absolute URL.
- Design tokens live in web/src/app/globals.css (light and dark). Shared components in web/src/components/ui (Button, TextField, StatusBadge, Alert, Spinner, ConfirmDialog, PageHeader, Brand). Reuse and extend them. Do not fork a second design system.
- Tests: Vitest + Testing Library (`npm test`), Playwright + axe (`npm run e2e`). Keep them green. Update the tests you affect. Also run `npm run typecheck`, `npm run lint`, `npm run build`.

HARD RULES
1. Only build UI for endpoints listed below. Do NOT call or display /dashboard/*, or GET /communities/{id}/members. They are stubs returning fake data.
2. No fabricated content: no invented stats, testimonials, customer logos, or "trusted by" claims.
3. Status always comes from the backend. Never show "Connected" or "Paid" because a button was clicked. Poll the real endpoint.
4. Colour is never the only signal. Every status has a text label and an icon.
5. Accessibility: WCAG 2.2 AA, keyboard-only operable, visible focus, skip link, landmarks, labelled form fields with errors wired by aria, reduced-motion respected, no horizontal scroll at 360px. axe must report zero violations.
6. Mobile first. Members will often come from a phone straight out of Telegram. Test at 360px, 768px and 1280px.
7. Plain, trustworthy voice. Avoid "seamless", "unlock", "supercharge". Prices in ₹ with 2 decimals, dates in the user's locale.
8. Never put tokens in localStorage. Access tokens stay in memory. Creator refresh uses the HttpOnly cookie.
9. Do not commit or push unless I ask. Never commit otp_dump.txt.

API CONTRACT (prefix /api/v1; success = {success:true,data}; errors = {success:false,message,error_code} or {detail})

CREATOR AUTH
- POST /auth/register {name, username, email, phone?}                  → /signup
- POST /auth/request-otp {identifier(email|username)}                  → /login step 1 (always shows a generic "if an account exists, a code was sent")
- POST /auth/verify-otp {identifier, otp_code}  → {access_token}        → /login step 2
- POST /auth/refresh, POST /auth/logout                                → app shell, session restore
- GET /auth/me                                                          → Settings page (not wired yet)
- PUT /auth/phone {phone with country code}                             → Onboarding step 1
CREATOR TELEGRAM ACCOUNT LINK
- POST /telegram/connect/creator → {telegram_link, expires_at}          → Onboarding step 2 (open link)
- GET  /telegram/connect/creator → {connected, telegram_username, linked_at} → poll every ~3s
COMMUNITIES
- POST /communities {name, description?}  (errors: TELEGRAM_NOT_CONNECTED, PENDING_TELEGRAM_CONNECTION)
- GET /communities/active|inactive?page&page_size
- GET/PATCH /communities/{id};  PATCH /communities/{id}/activate|deactivate
GROUP CONNECTION (no "connect" call; creator adds the bot to the group as admin with "Invite users via link" + "Ban users"; the UI shows instructions and polls)
- GET /telegram/communities/{id}/status → {status: NOT_CONNECTED|CONNECTED|NEEDS_ATTENTION (legacy CONNECTING|DISCONNECTED), telegram_chat_id, connected_at}
- DELETE /telegram/communities/{id}  (204)  → "Disconnect group" danger action (NEW UI)
- DELETE /telegram/communities/{id}/members/{member_id} → {telegram_removal: DONE|QUEUED|NOT_NEEDED|ALREADY_REMOVED}; 409 if plan still active. (Design the result states, but there is no member list endpoint yet, so do not ship a fake table.)
PLANS
- POST /communities/{id}/plans {name 2-100, description?≤500, price ₹≥1 (2dp), duration_days 1-3650}  (errors: COMMUNITY_NOT_CONNECTED, DUPLICATE_PLAN_NAME)
- GET /communities/{id}/plans;  PATCH /plans/{id};  PATCH /plans/{id}/activate|deactivate
  Plan = {id, name, description, price_paise, price, currency, duration_days, is_active}
MEMBER
- POST /members/register {name, email, phone}; POST /members/request-otp {email}; POST /members/verify-otp {email, otp_code}→{access_token}; GET /members/me → {name,email,phone,telegram_connected,…}
- POST/GET /telegram/connect/member  (phone shared in Telegram must match the member's phone)
- GET /communities/{id}/plans/available  (member token)
- POST /plans/{plan_id}/payment-link → {id, payment_link_url, amount_paise, status, expires_at} (errors: PLAN_UNAVAILABLE, PLAN_NOT_FOUND, 502)
- GET /payments/{id} → status created|paid|expired|cancelled (poll ~3s until terminal)
- GET /subscriptions/me → {subscriptions:[{id, plan_id, status: active|expired|cancelled|pending, starts_at, ends_at, cancelled_at}], total}
- GET /subscriptions/{id}
- POST /telegram/communities/{id}/invite → {invite_link}   (member with active plan + linked Telegram) → "Join Telegram group" button (NEW UI)
Member auth has NO refresh endpoint: on 401, send the member to /m/login with a safe `next` param.

SCREENS TO DESIGN AND IMPLEMENT (keep existing routes)
Public site: / , /how-it-works, /telegram-bot, /faq, /privacy, /terms, /contact
  - Home hero should show a real, static product-state demo (status badges, plan card), not stock art.
Creator: /signup, /login (2-step OTP, 6-box code input with paste support and resend countdown), /app (communities, Active/Inactive tabs, pagination, empty states), /app/onboarding (3-step stepper: phone → Telegram → first community; skip completed steps), /app/communities/new, /app/communities/[id] (header + edit, connection panel, plans table/cards, activate/deactivate with confirm), /app/settings (profile from GET /auth/me, Telegram link state, logout).
Member: /m/signup, /m/login, /m/connect-telegram, /c/[communityId] (plan cards → Pay), /m/payments/[id] (state machine page), /m/subscriptions (cards with status, dates, days remaining, "Join Telegram group" when active).

KEY UX FLOWS (design each state explicitly)
1. Creator onboarding: stepper with the real state of each step. Telegram link shows "waiting for you to open Telegram…" with a spinner, then success. Handle expired link (offer a new one).
2. Group connection panel states:
   - NOT_CONNECTED: numbered instructions (add @<NEXT_PUBLIC_TELEGRAM_BOT_USERNAME> to the group → make admin → enable "Invite users via link" and "Ban users"), a copy-bot-username button, and an auto-updating "waiting…" indicator.
   - CONNECTED: chat ID (mono font), connected date, "Disconnect group" in a danger zone with a confirm dialog.
   - NEEDS_ATTENTION: what to fix (admin rights, or re-add the bot). The backend does not say which permission is missing, so word it generically.
   - Plans are disabled, with an explanation, until CONNECTED.
3. Plans: price input with a ₹ prefix, duration in days (offer quick presets like 7/30/90/365 plus custom), inline field errors, DUPLICATE_PLAN_NAME shown on the name field.
4. Member pay flow: plan card → "Pay ₹X" → create link → open payment_link_url → return to /m/payments/[id]:
   created = "Waiting for payment" (+ open-link-again button, expiry time),
   paid = success with a primary "Join Telegram group" button (calls the invite endpoint, opens invite_link) and a note that the bot also DMs the same button,
   expired / cancelled = clear retry action.
   Block payment with a clear prompt if the member has not connected Telegram.
5. Subscriptions: status chips (active / expired / cancelled / pending) with icon + text, start and end dates, "ends in N days", a Renew action for expired ones (links back to the community plans page). The API returns only plan_id, so do NOT invent plan or community names. Use only the data returned, or fetch it through an endpoint that exists, and tell me what is missing.
6. Errors: map error_code to friendly copy. Handle NETWORK_ERROR, rate limits and OTP errors (invalid, expired, too many attempts). Always offer a next step.
7. Loading, empty, and error states for every list and page (skeletons, not spinners, for lists).

DESIGN DIRECTION
- Notion-like structure and consistency, with real product states instead of stock imagery. Calm, dense-but-readable, trustworthy. Borders over shadows.
- Keep or refine the existing tokens: canvas #F8F8F6, ink #191B22, accent #3d5fdc (a single CSS variable), semantic success/warning/danger/info/neutral each with a -soft background, radii 6px (controls) and 12px (cards), spacing 4/8/12/16/24/32/48/64/96. Light and dark via prefers-color-scheme plus a data-theme override.
- Type: Geist Sans, Geist Mono for IDs. Display 48-56, section 36, card 20, body 16, label 13.
- Motion: subtle, 150-200ms, disabled under prefers-reduced-motion.
- Same design system on the public site and the app, with different layouts: marketing pages are airy, the creator app is a sidebar + content layout, the member portal is a minimal top-bar layout optimised for phones.

DELIVERABLES
1. A short design note (docs/ui-redesign.md): IA, token changes, component inventory, and each state you designed.
2. Implemented components and pages, reusing the existing API client, hooks and components wherever they fit.
3. Updated unit and E2E tests (mock API in web/e2e/mock-api.ts). The new invite and disconnect flows need tests.
4. Passing: `npm test`, `npm run typecheck`, `npm run lint`, `npm run build`, `npm run e2e`.
5. A final report listing every endpoint touched, what you could not build because the backend lacks it, and any assumption you made.

WORK STEP BY STEP: (1) tokens and shared components, (2) auth screens, (3) onboarding and communities, (4) connection panel and plans, (5) member flow, (6) public site, (7) a11y/mobile/E2E pass. Finish each step with tests green, summarise, then continue.
````
