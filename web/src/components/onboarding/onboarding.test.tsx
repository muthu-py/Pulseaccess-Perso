import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CommunitiesHome } from "@/components/app/CommunitiesHome";
import { session } from "@/lib/api/client";

import { Onboarding } from "./Onboarding";

const router = { push: vi.fn(), replace: vi.fn() };
vi.mock("next/navigation", () => ({ useRouter: () => router }));

function respond(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}
const ok = (data: unknown) => respond(200, { success: true, data });
const fail = (status: number, code: string) => respond(status, { success: false, message: code, error_code: code });
const list = (total: number) => ok({ communities: [], page: 1, page_size: 1, total });

type Handler = (init: RequestInit) => Response;

/** Routes "METHOD /path" to a handler; unmatched calls return 500 so tests fail loudly. */
function mockApi(routes: Record<string, Handler>) {
  const fetchMock = vi.fn(async (url: string, init: RequestInit = {}) => {
    const key = `${init.method ?? "GET"} ${url.replace("/api/v1", "").split("?")[0]}`;
    const handler = routes[key];
    return handler ? handler(init) : respond(500, { detail: `unmocked ${key}` });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderWithClient(ui: React.ReactElement) {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  router.push.mockReset();
  router.replace.mockReset();
  session.set("tok");
});

describe("Onboarding", () => {
  it("shows the Telegram step first and opens the bot link after connecting", async () => {
    mockApi({
      "GET /telegram/connect/creator": () => ok({ connected: false }),
      "POST /telegram/connect/creator": () =>
        ok({ telegram_link: "https://t.me/bot?start=abc", expires_at: new Date(Date.now() + 600000).toISOString() }),
      "GET /communities/active": () => list(0),
      "GET /communities/inactive": () => list(0),
    });
    renderWithClient(<Onboarding />);

    await userEvent.click(await screen.findByRole("button", { name: /connect telegram/i }));

    const link = await screen.findByRole("link", { name: /open telegram/i });
    expect(link).toHaveAttribute("href", "https://t.me/bot?start=abc");
    expect(screen.getByText(/waiting for telegram to confirm/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/community name/i)).not.toBeInTheDocument();
  });

  it("asks for a phone when the backend requires one, then retries the connect", async () => {
    let phoneSaved = false;
    const fetchMock = mockApi({
      "GET /telegram/connect/creator": () => ok({ connected: false }),
      "POST /telegram/connect/creator": () =>
        phoneSaved
          ? ok({ telegram_link: "https://t.me/bot?start=xyz", expires_at: new Date(Date.now() + 600000).toISOString() })
          : fail(400, "PHONE_REQUIRED"),
      "PUT /auth/phone": () => {
        phoneSaved = true;
        return ok({});
      },
      "GET /communities/active": () => list(0),
      "GET /communities/inactive": () => list(0),
    });
    renderWithClient(<Onboarding />);

    await userEvent.click(await screen.findByRole("button", { name: /connect telegram/i }));
    await userEvent.type(await screen.findByLabelText(/phone number/i), "+919876543210");
    await userEvent.click(screen.getByRole("button", { name: /save phone number/i }));

    expect(await screen.findByRole("link", { name: /open telegram/i })).toBeInTheDocument();
    const put = fetchMock.mock.calls.find(([url]) => url === "/api/v1/auth/phone");
    expect(JSON.parse(put![1]!.body as string)).toEqual({ phone: "+919876543210" });
  });

  it("rejects a phone without a country code before calling the API", async () => {
    const fetchMock = mockApi({
      "GET /telegram/connect/creator": () => ok({ connected: false }),
      "POST /telegram/connect/creator": () => fail(400, "PHONE_REQUIRED"),
      "GET /communities/active": () => list(0),
      "GET /communities/inactive": () => list(0),
    });
    renderWithClient(<Onboarding />);

    await userEvent.click(await screen.findByRole("button", { name: /connect telegram/i }));
    await userEvent.type(await screen.findByLabelText(/phone number/i), "98765");
    await userEvent.click(screen.getByRole("button", { name: /save phone number/i }));

    expect(screen.getByLabelText(/phone number/i)).toHaveAccessibleDescription(/country code/i);
    expect(fetchMock.mock.calls.some(([url]) => url === "/api/v1/auth/phone")).toBe(false);
  });

  it("shows the community form once Telegram is connected and creates the community", async () => {
    let created = false;
    mockApi({
      "GET /telegram/connect/creator": () => ok({ connected: true, telegram_username: "asha" }),
      "GET /communities/active": () => list(created ? 1 : 0),
      "GET /communities/inactive": () => list(0),
      "POST /communities": () => {
        created = true;
        return respond(201, { success: true, data: { id: "c1", name: "Java Masters" } });
      },
    });
    renderWithClient(<Onboarding />);

    await userEvent.type(await screen.findByLabelText(/community name/i), "Java Masters");
    await userEvent.click(screen.getByRole("button", { name: /create community/i }));

    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/app"));
  });

  it("validates the community name length", async () => {
    const fetchMock = mockApi({
      "GET /telegram/connect/creator": () => ok({ connected: true }),
      "GET /communities/active": () => list(0),
      "GET /communities/inactive": () => list(0),
    });
    renderWithClient(<Onboarding />);

    await userEvent.type(await screen.findByLabelText(/community name/i), "ab");
    await userEvent.click(screen.getByRole("button", { name: /create community/i }));

    expect(screen.getByLabelText(/community name/i)).toHaveAccessibleDescription(/3 to 100/);
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === "POST")).toBe(false);
  });

  it("explains PENDING_TELEGRAM_CONNECTION", async () => {
    mockApi({
      "GET /telegram/connect/creator": () => ok({ connected: true }),
      "GET /communities/active": () => list(0),
      "GET /communities/inactive": () => list(0),
      "POST /communities": () => fail(409, "PENDING_TELEGRAM_CONNECTION"),
    });
    renderWithClient(<Onboarding />);

    await userEvent.type(await screen.findByLabelText(/community name/i), "Java Masters");
    await userEvent.click(screen.getByRole("button", { name: /create community/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/waiting to be connected/i);
  });

  it("leaves onboarding when Telegram is connected and a community exists", async () => {
    mockApi({
      "GET /telegram/connect/creator": () => ok({ connected: true }),
      "GET /communities/active": () => list(1),
      "GET /communities/inactive": () => list(0),
    });
    renderWithClient(<Onboarding />);
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/app"));
  });
});

describe("CommunitiesHome", () => {
  it("redirects new creators to onboarding when Telegram is not connected", async () => {
    mockApi({
      "GET /telegram/connect/creator": () => ok({ connected: false }),
      "GET /communities/active": () => list(0),
      "GET /communities/inactive": () => list(0),
    });
    renderWithClient(<CommunitiesHome />);
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/app/onboarding"));
  });

  it("redirects when connected but no community exists yet", async () => {
    mockApi({
      "GET /telegram/connect/creator": () => ok({ connected: true }),
      "GET /communities/active": () => list(0),
      "GET /communities/inactive": () => list(0),
    });
    renderWithClient(<CommunitiesHome />);
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/app/onboarding"));
  });

  it("stays put for a set-up creator", async () => {
    mockApi({
      "GET /telegram/connect/creator": () => ok({ connected: true }),
      "GET /communities/active": () => list(2),
      "GET /communities/inactive": () => list(1),
    });
    renderWithClient(<CommunitiesHome />);
    expect(await screen.findByText(/you have 3 communities/i)).toBeInTheDocument();
    expect(router.replace).not.toHaveBeenCalled();
  });
});
