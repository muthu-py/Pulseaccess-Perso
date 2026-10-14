import type { Page, Route } from "@playwright/test";

/** In-browser fake of the PulseAccess API. Tests flip `state` to simulate what Telegram and Razorpay do. */
export type MockState = {
  creatorLoggedIn: boolean;
  creatorTelegramLinkRequested: boolean;
  creatorTelegramConnected: boolean;
  communities: { id: string; name: string; description: string | null }[];
  groupStatus: "NOT_CONNECTED" | "CONNECTED" | "NEEDS_ATTENTION";
  plans: Record<string, unknown>[];
  memberLoggedIn: boolean;
  memberTelegramConnected: boolean;
  paymentStatus: "created" | "paid" | "expired" | "cancelled";
  requests: string[];
};

export function initialState(): MockState {
  return {
    creatorLoggedIn: false,
    creatorTelegramLinkRequested: false,
    creatorTelegramConnected: false,
    communities: [],
    groupStatus: "NOT_CONNECTED",
    plans: [],
    memberLoggedIn: false,
    memberTelegramConnected: true,
    paymentStatus: "created",
    requests: [],
  };
}

const ok = (data: unknown, status = 200) => ({
  status,
  contentType: "application/json",
  body: JSON.stringify({ success: true, data }),
});
const fail = (status: number, code: string, message = code) => ({
  status,
  contentType: "application/json",
  body: JSON.stringify({ success: false, message, error_code: code }),
});

const community = (c: MockState["communities"][number], connected: boolean) => ({
  ...c,
  is_active: true,
  telegram_connected: connected,
  created_at: "2026-10-01T00:00:00Z",
});

const PLAN = {
  id: "p1",
  community_id: "c1",
  name: "Monthly",
  description: null,
  price_paise: 49900,
  price: "499.00",
  currency: "INR",
  duration_days: 30,
  is_active: true,
  created_at: "2026-10-01T00:00:00Z",
};

export async function mockApi(page: Page, state: MockState) {
  await page.route("**/api/v1/**", async (route: Route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname.replace("/api/v1", "");
    const key = `${req.method()} ${path}`;
    state.requests.push(key);
    const body = req.postDataJSON?.() ?? null;
    const auth = req.headers()["authorization"] ?? "";

    // ---- creator auth
    if (key === "POST /auth/register") return route.fulfill(ok({ creator: { id: "u1" } }, 201));
    if (key === "POST /auth/request-otp") return route.fulfill(ok({ message: "sent" }));
    if (key === "POST /auth/verify-otp") {
      if (body?.otp_code !== "123456") return route.fulfill(fail(401, "INVALID_OTP"));
      state.creatorLoggedIn = true;
      return route.fulfill(ok({ access_token: "creator-token", token_type: "bearer" }));
    }
    if (key === "POST /auth/refresh") {
      return state.creatorLoggedIn
        ? route.fulfill(ok({ access_token: "creator-token", token_type: "bearer" }))
        : route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "no session" }) });
    }
    if (key === "GET /auth/me") {
      return auth === "Bearer creator-token"
        ? route.fulfill(ok({ id: "u1", name: "Naveen", username: "naveen_k", email: "naveen@example.com", phone: null, is_active: true, created_at: "2026-10-01T00:00:00Z" }))
        : route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "Not authenticated" }) });
    }
    if (key === "POST /auth/logout") {
      state.creatorLoggedIn = false;
      return route.fulfill(ok({ message: "bye" }));
    }

    // ---- creator telegram + communities
    if (key === "GET /telegram/connect/creator") {
      if (state.creatorTelegramLinkRequested) state.creatorTelegramConnected = true; // user "finished" in Telegram
      return route.fulfill(ok({ connected: state.creatorTelegramConnected, telegram_username: "creator" }));
    }
    if (key === "POST /telegram/connect/creator") {
      state.creatorTelegramLinkRequested = true;
      return route.fulfill(
        ok({ telegram_link: "https://t.me/PulseAccessBot?start=abc", expires_at: new Date(Date.now() + 600000).toISOString() }),
      );
    }
    if (key === "GET /communities/active") {
      const list = state.communities.map((c) => community(c, state.groupStatus === "CONNECTED"));
      return route.fulfill(ok({ communities: list, page: 1, page_size: 10, total: list.length }));
    }
    if (key === "GET /communities/inactive") return route.fulfill(ok({ communities: [], page: 1, page_size: 10, total: 0 }));
    if (key === "POST /communities") {
      const created = { id: "c1", name: body.name, description: body.description ?? null };
      state.communities.push(created);
      return route.fulfill(ok(community(created, false), 201));
    }
    if (key === "GET /communities/c1") {
      const c = state.communities[0];
      return c ? route.fulfill(ok(community(c, state.groupStatus === "CONNECTED"))) : route.fulfill(fail(404, "COMMUNITY_NOT_FOUND"));
    }
    if (key === "GET /telegram/communities/c1/status") {
      return route.fulfill(
        ok({ status: state.groupStatus, telegram_chat_id: state.groupStatus === "CONNECTED" ? "-1001234567890" : null, connected_at: null }),
      );
    }
    if (key === "GET /communities/c1/plans") return route.fulfill(ok(state.plans));
    if (key === "POST /communities/c1/plans") {
      const plan = { ...PLAN, name: body.name, price: body.price, price_paise: Math.round(Number(body.price) * 100), duration_days: body.duration_days };
      state.plans.push(plan);
      return route.fulfill(ok(plan, 201));
    }

    // ---- member
    if (key === "POST /members/register") return route.fulfill(ok({}, 201));
    if (key === "POST /members/request-otp") return route.fulfill(ok({ message: "sent" }));
    if (key === "POST /members/verify-otp") {
      if (body?.otp_code !== "123456") return route.fulfill(fail(401, "INVALID_OTP"));
      state.memberLoggedIn = true;
      return route.fulfill(ok({ access_token: "member-token", token_type: "bearer" }));
    }
    if (path.startsWith("/members/") || path.startsWith("/payments/") || path.startsWith("/subscriptions/") || path.includes("/plans/available") || path.endsWith("/payment-link") || path === "/telegram/connect/member") {
      if (auth !== "Bearer member-token") return route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "Not authenticated" }) });
    }
    if (key === "GET /members/me") {
      return route.fulfill(ok({ id: "m1", name: "Ravi", email: "ravi@example.com", phone: "+919876543210", is_active: true, created_at: "2026-10-01T00:00:00Z", telegram_connected: state.memberTelegramConnected }));
    }
    if (key === "GET /telegram/connect/member") return route.fulfill(ok({ connected: state.memberTelegramConnected, telegram_username: "ravi" }));
    if (key === "GET /communities/c1/plans/available") return route.fulfill(ok([PLAN]));
    if (key === "POST /plans/p1/payment-link") {
      return route.fulfill(ok({ id: "pay1", plan_id: "p1", amount_paise: 49900, currency: "INR", status: "created", payment_link_url: "https://rzp.io/l/abc", expires_at: "2026-12-31T00:00:00Z", created_at: "2026-10-14T00:00:00Z" }, 201));
    }
    if (key === "GET /payments/pay1") {
      return route.fulfill(ok({ id: "pay1", plan_id: "p1", amount_paise: 49900, currency: "INR", status: state.paymentStatus, payment_link_url: "https://rzp.io/l/abc", expires_at: "2026-12-31T00:00:00Z", created_at: "2026-10-14T00:00:00Z" }));
    }
    if (key === "GET /subscriptions/me") {
      const subs = state.paymentStatus === "paid"
        ? [{ id: "s1", member_id: "m1", plan_id: "p1", status: "active", starts_at: "2026-10-14T00:00:00Z", ends_at: "2026-11-13T00:00:00Z", created_at: "2026-10-14T00:00:00Z" }]
        : [];
      return route.fulfill(ok({ subscriptions: subs, total: subs.length }));
    }

    return route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: `unmocked ${key}` }) });
  });
}
