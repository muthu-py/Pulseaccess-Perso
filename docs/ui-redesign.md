# PulseAccess UI/UX Design & Architecture Documentation

## 1. Information Architecture (IA)

PulseAccess is designed with clear layer separation across three distinct user contexts: **Marketing**, **Creator App**, and **Member Portal**.

```
PulseAccess
├── Public Marketing (Airy, SEO-indexed, Accessible)
│   ├── /                 - Product Hero, Static Demo, Feature Breakdown
│   ├── /how-it-works     - 3-Step Lifecycle: Connect Bot → Set Plans → Get Paid
│   ├── /telegram-bot     - Bot Permissions Guide & Security Explanation
│   ├── /faq              - Common Questions for Creators and Subscribers
│   └── /privacy, /terms, /contact
│
├── Creator Platform (Sidebar & Content, Dense, Productivity-Focused)
│   ├── /signup, /login   - 2-Step OTP Authentication, Session Resumption
│   ├── /app              - Communities Management (Active / Inactive Tabs, Pagination)
│   ├── /app/onboarding   - 3-Step Stepper: Phone → Telegram Bot Link → First Community
│   ├── /app/communities/new - Community Creation
│   ├── /app/communities/[id] - Overview, Group Connection, Share Link, Plans CRUD
│   └── /app/settings     - Profile (GET /auth/me), Phone, Telegram Account Link
│
└── Member Portal (Mobile-First, Top-Bar Minimal Shell, Fast Conversions)
    ├── /c/[communityId]  - Auth-Gated Community Access Plans & Checkout
    ├── /m/signup, /m/login - Member Email OTP Authentication with safe return redirect
    ├── /m/connect-telegram - Deep Link Linking Phone & Telegram Account
    ├── /m/payments/[id]  - Real-time Polling State Machine (created → paid)
    └── /m/subscriptions  - Active/Expired Passes with direct "Join Telegram group" CTA
```

---

## 2. Auth-Gated Share & Subscription Architecture

### The Problem
Creators need an effortless way to share a link with their audience (on Telegram channels, X, Instagram, or WhatsApp). Members who click that link must be guided through viewing plans, connecting Telegram, paying with Razorpay, and being added to the private Telegram group.

### The Implementation Flow
1. **Creator Link Generation (`/app/communities/[id]`)**:
   - The creator opens their community.
   - The **`ShareLink`** card renders the member URL: `https://<domain>/c/<communityId>`.
   - Offers one-click **"Copy link"** with instant visual feedback (`Copied!`) and a **"Preview"** button opening the member view in a new tab.
   - Status guards: Warns the creator if the Telegram group is not yet connected (`NOT_CONNECTED`) or if the community is deactivated.
2. **Member Link Landing & Auth-Gating (`/c/[communityId]`)**:
   - Prospective members open the shared URL.
   - Gated via `MemberShell`: Unauthenticated visitors are cleanly redirected to `/m/login?next=/c/<communityId>` (or `/m/signup`).
   - After entering their 6-digit email OTP, they are seamlessly returned to `/c/<communityId>` via `safeNext`.
3. **Plan Selection & Telegram Verification**:
   - Displays a 3-step progress helper: *1. Choose plan → 2. Connect Telegram → 3. Instant group invite*.
   - If the member has not yet connected Telegram, displays a prominent banner linking to `/m/connect-telegram?next=/c/<communityId>`.
   - Member picks their plan (e.g., ₹499 / 30 days) and clicks **"Pay ₹X"**.
4. **Checkout & Fulfillment (`/m/payments/[id]`)**:
   - Calls `POST /plans/{plan_id}/payment-link`, receiving the Razorpay link.
   - Redirects to `/m/payments/[id]?communityId=<communityId>`.
   - Polls `GET /payments/{id}` every 3 seconds.
   - While `created`: Shows "Waiting for payment" and an external link to Razorpay.
   - On `paid`: Shows confirmation and a primary **"Join Telegram group"** button that invokes `POST /telegram/communities/{id}/invite` to open the single-use invite link.

---

## 3. Design Tokens & Design System

Tokens are declared centrally in `web/src/app/globals.css` with support for light mode, dark mode (via `data-theme` or `prefers-color-scheme`), and `prefers-reduced-motion`.

| Token Category | Values / Implementations |
|---|---|
| **Canvas & Surfaces** | `--canvas: #F8F8F6` (Light), `#0D0F12` (Dark); `--surface: #FFFFFF` / `#161920`; `--surface-sunken: #F0F0EC` / `#111318` |
| **Ink (Typography)** | `--ink: #191B22` (High contrast), `--ink-muted: #5E6370`, `--ink-subtle: #8F95A3` |
| **Accent** | `--accent: #3d5fdc` (Single CSS variable brand accent), `--accent-ink: #FFFFFF` |
| **Semantic Tones** | `success` (`#15803d`), `warning` (`#b45309`), `danger` (`#b91c1c`), `neutral` (`#475569`) with `-soft` background tints |
| **Typography** | `Geist Sans` for UI, `Geist Mono` for IDs (Payment IDs, Chat IDs, Hashes) |
| **Radii** | Controls: `6px` (`--radius-control`), Cards: `12px` (`--radius-card`), Passes: `16px` (`--radius-pass`) |

---

## 4. Component Inventory

1. **Primitives (`web/src/components/ui/`)**:
   - `Button`: Multiple variants (`primary`, `secondary`, `ghost`, `danger`), sizes (`sm`, `md`, `lg`), busy/loading spinner states.
   - `TextField`: Accessible input with floating label, description, and ARIA error bindings.
   - `StatusBadge`: Dual icon + text status indicators across connection, payment, and membership domains.
   - `Alert`: Semantic alert boxes (`info`, `success`, `warning`, `danger`) with readable contrast.
   - `ConfirmDialog`: Modal confirmation for destructive operations (Activate, Deactivate, Disconnect Group).
   - `Spinner` & `Pulse`: Reduced-motion respecting activity indicators.
   - `PageHeader`, `LoadingRow`, `EmptyState`: Standardized layout frames.

2. **Domain Modules**:
   - `ShareLink`: Copyable member URL widget with clipboard feedback, preview link, and status warnings.
   - `ConnectionPanel`: 3-step bot setup instructions, bot username copy, real-time polling, danger-zone group disconnection.
   - `PlansSection`: Creator plan creation modal, pricing in ₹, preset durations, and duplicate name validation.
   - `CommunityPlans`: Member plan selection, 3-step value guide, Telegram connect prompt, and checkout trigger.
   - `PaymentStatus`: Real-time payment state machine receipt with Telegram invite link button.
   - `Subscriptions`: Subscriber membership overview with remaining days and direct invite links.
   - `SettingsView`: Creator profile overview wired to `GET /auth/me`.

---

## 5. Verification Metrics

- **Unit Tests (`vitest`)**: 10 passed test suites, **98 / 98 tests green** (100% pass rate).
- **E2E Tests (`playwright`)**: **40 / 40 tests green** across Desktop Chrome and Mobile Safari.
- **Accessibility (`@axe-core/playwright`)**: **0 WCAG 2.2 AA violations**.
- **TypeScript (`tsc --noEmit`)**: 0 type errors.
- **ESLint**: 0 errors, 0 warnings.
- **Next.js 16 Production Build**: All 27 static and partial-prerender routes compiled.
