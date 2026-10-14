import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { session } from "@/lib/api/client";

import { CommunityPlans } from "./CommunityPlans";
import { PaymentStatus } from "./PaymentStatus";
import { Subscriptions } from "./Subscriptions";

const router = { push: vi.fn(), replace: vi.fn() };
let params: Record<string, string> = {};
vi.mock("next/navigation", () => ({ useRouter: () => router, useParams: () => params }));

function respond(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}
const ok = (data: unknown) => respond(200, { success: true, data });
const fail = (status: number, code: string) => respond(status, { success: false, message: code, error_code: code });

type Handler = (init: RequestInit) => Response;
function mockApi(routes: Record<string, Handler>) {
  const fetchMock = vi.fn(async (url: string, init: RequestInit = {}) => {
    const key = `${init.method ?? "GET"} ${url.replace("/api/v1", "")}`;
    const handler = routes[key];
    return handler ? handler(init) : respond(500, { detail: `unmocked ${key}` });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function wrap(ui: React.ReactElement) {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>{ui}</QueryClientProvider>,
  );
}

const plan = (over: object = {}) => ({
  id: "p1",
  community_id: "c1",
  name: "Monthly",
  description: "Everything",
  price_paise: 49900,
  price: "499.00",
  currency: "INR",
  duration_days: 30,
  is_active: true,
  created_at: "2026-10-01T00:00:00Z",
  ...over,
});
const payment = (over: object = {}) => ({
  id: "pay1",
  plan_id: "p1",
  amount_paise: 49900,
  currency: "INR",
  status: "created",
  payment_link_url: "https://rzp.io/l/abc",
  expires_at: "2026-10-15T00:00:00Z",
  created_at: "2026-10-14T00:00:00Z",
  ...over,
});

beforeEach(() => {
  router.push.mockReset();
  router.replace.mockReset();
  session.set("mtok", "member");
});
afterEach(() => vi.useRealTimers());

describe("CommunityPlans", () => {
  beforeEach(() => {
    params = { communityId: "c1" };
  });

  it("lists plans and goes to the payment page after creating a link", async () => {
    const fetchMock = mockApi({
      "GET /communities/c1/plans/available": () => ok([plan()]),
      "GET /telegram/connect/member": () => ok({ connected: true }),
      "POST /plans/p1/payment-link": () => respond(201, { success: true, data: payment() }),
    });
    wrap(<CommunityPlans />);

    expect(await screen.findByText("for 30 days")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Pay for Monthly" }));

    await vi.waitFor(() => expect(router.push).toHaveBeenCalledWith("/m/payments/pay1"));
    const post = fetchMock.mock.calls.find(([, init]) => init?.method === "POST")!;
    expect((post[1]!.headers as Record<string, string>).Authorization).toBe("Bearer mtok");
  });

  it("asks the member to connect Telegram first, and sends them back here after", async () => {
    mockApi({
      "GET /communities/c1/plans/available": () => ok([plan()]),
      "GET /telegram/connect/member": () => ok({ connected: false }),
    });
    wrap(<CommunityPlans />);

    const link = await screen.findByRole("link", { name: "Connect Telegram" });
    expect(link).toHaveAttribute("href", "/m/connect-telegram?next=%2Fc%2Fc1");
  });

  it("shows the Telegram prompt when paying is refused for that reason", async () => {
    mockApi({
      "GET /communities/c1/plans/available": () => ok([plan()]),
      "GET /telegram/connect/member": () => ok({ connected: true }),
      "POST /plans/p1/payment-link": () => fail(403, "TELEGRAM_NOT_CONNECTED"),
    });
    wrap(<CommunityPlans />);

    await userEvent.click(await screen.findByRole("button", { name: "Pay for Monthly" }));
    expect(await screen.findByText(/connect telegram before you pay/i)).toBeInTheDocument();
    expect(router.push).not.toHaveBeenCalled();
  });

  it("explains an unavailable plan and a payment-provider failure", async () => {
    let code = "PLAN_UNAVAILABLE";
    mockApi({
      "GET /communities/c1/plans/available": () => ok([plan()]),
      "GET /telegram/connect/member": () => ok({ connected: true }),
      "POST /plans/p1/payment-link": () => (code === "HTTP_502" ? respond(502, { detail: "bad gateway" }) : fail(409, code)),
    });
    wrap(<CommunityPlans />);

    await userEvent.click(await screen.findByRole("button", { name: "Pay for Monthly" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/isn't available any more/i);

    code = "HTTP_502";
    await userEvent.click(screen.getByRole("button", { name: "Pay for Monthly" }));
    await vi.waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/payment provider didn't respond/i));
  });

  it("shows an empty state", async () => {
    mockApi({
      "GET /communities/c1/plans/available": () => ok([]),
      "GET /telegram/connect/member": () => ok({ connected: true }),
    });
    wrap(<CommunityPlans />);
    expect(await screen.findByText(/no plans are available/i)).toBeInTheDocument();
  });
});

describe("PaymentStatus", () => {
  beforeEach(() => {
    params = { id: "pay1" };
  });

  it("shows the pay link while open, then flips to paid from the backend and stops polling", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(async () => ok(payment()))
      .mockImplementation(async () => ok(payment({ status: "paid" })));
    vi.stubGlobal("fetch", fetchMock);
    wrap(<PaymentStatus />);

    expect(await screen.findByText("Awaiting payment")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /pay ₹499.00 on razorpay/i })).toHaveAttribute("href", "https://rzp.io/l/abc");

    await act(() => vi.advanceTimersByTimeAsync(3100));
    expect(await screen.findByText("Payment received.")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /razorpay/i })).not.toBeInTheDocument();

    const calls = fetchMock.mock.calls.length;
    await act(() => vi.advanceTimersByTimeAsync(10000));
    expect(fetchMock.mock.calls.length).toBe(calls);
  });

  it.each(["expired", "cancelled"])("explains a %s payment without offering the link", async (status) => {
    mockApi({ "GET /payments/pay1": () => ok(payment({ status })) });
    wrap(<PaymentStatus />);

    expect(await screen.findByText(/you were not charged for this link/i)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /razorpay/i })).not.toBeInTheDocument();
  });

  it("shows a not-found error", async () => {
    mockApi({ "GET /payments/pay1": () => fail(404, "PAYMENT_NOT_FOUND") });
    wrap(<PaymentStatus />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/couldn't find this payment/i);
  });
});

describe("Subscriptions", () => {
  it("lists subscriptions with a text status", async () => {
    mockApi({
      "GET /subscriptions/me": () =>
        ok({
          total: 2,
          subscriptions: [
            { id: "s1", member_id: "m1", plan_id: "p1", status: "active", starts_at: "2026-10-01T00:00:00Z", ends_at: "2026-10-31T00:00:00Z", created_at: "2026-10-01T00:00:00Z" },
            { id: "s2", member_id: "m1", plan_id: "p1", status: "expired", starts_at: "2026-08-01T00:00:00Z", ends_at: "2026-08-31T00:00:00Z", created_at: "2026-08-01T00:00:00Z" },
          ],
        }),
    });
    wrap(<Subscriptions />);

    const items = await screen.findAllByRole("listitem");
    expect(within(items[0]).getByText("Active")).toBeInTheDocument();
    expect(within(items[1]).getByText("Expired")).toBeInTheDocument();
  });

  it("shows an empty state", async () => {
    mockApi({ "GET /subscriptions/me": () => ok({ total: 0, subscriptions: [] }) });
    wrap(<Subscriptions />);
    expect(await screen.findByText(/no subscriptions yet/i)).toBeInTheDocument();
  });
});
