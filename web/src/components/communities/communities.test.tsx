import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { session } from "@/lib/api/client";

import { CommunityDetail } from "./CommunityDetail";
import { CommunityList } from "./CommunityList";
import { NewCommunity } from "./NewCommunity";

const router = { push: vi.fn(), replace: vi.fn() };
vi.mock("next/navigation", () => ({ useRouter: () => router, useParams: () => ({ id: "c1" }) }));

function respond(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}
const ok = (data: unknown) => respond(200, { success: true, data });
const fail = (status: number, code: string) => respond(status, { success: false, message: code, error_code: code });

const community = (over: object = {}) => ({
  id: "c1",
  name: "Java Masters",
  description: "Weekly deep dives",
  is_active: true,
  telegram_connected: false,
  created_at: "2026-10-01T00:00:00Z",
  ...over,
});
const list = (communities: object[], total = communities.length) => ok({ communities, page: 1, page_size: 10, total });

type Handler = (init: RequestInit) => Response;

function mockApi(routes: Record<string, Handler>) {
  const fetchMock = vi.fn(async (url: string, init: RequestInit = {}) => {
    const key = `${init.method ?? "GET"} ${url.replace("/api/v1", "")}`;
    const handler = routes[key] ?? routes[key.split("?")[0]];
    return handler ? handler(init) : respond(500, { detail: `unmocked ${key}` });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderWithClient(ui: React.ReactElement) {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>{ui}</QueryClientProvider>,
  );
}

beforeEach(() => {
  router.push.mockReset();
  router.replace.mockReset();
  session.set("tok");
});

describe("CommunityList", () => {
  it("lists active communities with a text connection status and links to each", async () => {
    mockApi({
      "GET /communities/active?page=1&page_size=10": () =>
        list([community(), community({ id: "c2", name: "Rustaceans", description: null, telegram_connected: true })]),
    });
    renderWithClient(<CommunityList />);

    const link = await screen.findByRole("link", { name: /java masters/i });
    expect(link).toHaveAttribute("href", "/app/communities/c1");
    expect(within(link).getByText("Not connected")).toBeInTheDocument();
    expect(within(screen.getByRole("link", { name: /rustaceans/i })).getByText("Connected")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /new community/i })).toHaveAttribute("href", "/app/communities/new");
  });

  it("switches to the Inactive tab", async () => {
    mockApi({
      "GET /communities/active?page=1&page_size=10": () => list([community()]),
      "GET /communities/inactive?page=1&page_size=10": () => list([community({ id: "c9", name: "Old group", is_active: false })]),
    });
    renderWithClient(<CommunityList />);
    await screen.findByRole("link", { name: /java masters/i });

    await userEvent.click(screen.getByRole("tab", { name: "Inactive" }));

    expect(await screen.findByRole("link", { name: /old group/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Inactive" })).toHaveAttribute("aria-selected", "true");
  });

  it("shows an empty state", async () => {
    mockApi({ "GET /communities/active?page=1&page_size=10": () => list([]) });
    renderWithClient(<CommunityList />);
    expect(await screen.findByText(/no active communities/i)).toBeInTheDocument();
  });

  it("paginates", async () => {
    mockApi({
      "GET /communities/active?page=1&page_size=10": () => list([community()], 25),
      "GET /communities/active?page=2&page_size=10": () => list([community({ id: "c3", name: "Page two" })], 25),
    });
    renderWithClient(<CommunityList />);

    await screen.findByText("Page 1 of 3");
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Next" }));

    expect(await screen.findByRole("link", { name: /page two/i })).toBeInTheDocument();
    expect(screen.getByText("Page 2 of 3")).toBeInTheDocument();
  });
});

describe("NewCommunity", () => {
  it("creates and opens the new community", async () => {
    const fetchMock = mockApi({ "POST /communities": () => respond(201, { success: true, data: community({ id: "new1" }) }) });
    renderWithClient(<NewCommunity />);

    await userEvent.type(screen.getByLabelText(/community name/i), "Java Masters");
    await userEvent.type(screen.getByLabelText(/description/i), "Weekly deep dives");
    await userEvent.click(screen.getByRole("button", { name: /create community/i }));

    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/app/communities/new1"));
    const post = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
    expect(JSON.parse(post![1]!.body as string)).toEqual({ name: "Java Masters", description: "Weekly deep dives" });
  });

  it("shows a duplicate-name error on the field", async () => {
    mockApi({ "POST /communities": () => fail(409, "DUPLICATE_COMMUNITY_NAME") });
    renderWithClient(<NewCommunity />);

    await userEvent.type(screen.getByLabelText(/community name/i), "Java Masters");
    await userEvent.click(screen.getByRole("button", { name: /create community/i }));

    await waitFor(() =>
      expect(screen.getByLabelText(/community name/i)).toHaveAccessibleDescription(/already have a community/i),
    );
  });

  it("explains a pending Telegram connection", async () => {
    mockApi({ "POST /communities": () => fail(409, "PENDING_TELEGRAM_CONNECTION") });
    renderWithClient(<NewCommunity />);

    await userEvent.type(screen.getByLabelText(/community name/i), "Another one");
    await userEvent.click(screen.getByRole("button", { name: /create community/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/waiting to be connected/i);
  });
});

describe("CommunityDetail", () => {
  it("edits name and description", async () => {
    let current = community();
    const fetchMock = mockApi({
      "GET /communities/c1": () => ok(current),
      "PATCH /communities/c1": (init) => {
        current = community(JSON.parse(init.body as string));
        return ok(current);
      },
    });
    renderWithClient(<CommunityDetail />);

    await userEvent.click(await screen.findByRole("button", { name: /edit details/i }));
    const name = screen.getByLabelText(/community name/i);
    expect(name).toHaveValue("Java Masters");
    await userEvent.clear(name);
    await userEvent.type(name, "Java Pros");
    await userEvent.click(screen.getByRole("button", { name: /save changes/i }));

    expect(await screen.findByRole("heading", { name: "Java Pros" })).toBeInTheDocument();
    const patch = fetchMock.mock.calls.find(([, init]) => init?.method === "PATCH");
    expect(JSON.parse(patch![1]!.body as string)).toEqual({ name: "Java Pros", description: "Weekly deep dives" });
  });

  it("asks for confirmation before deactivating, and Cancel does nothing", async () => {
    const fetchMock = mockApi({ "GET /communities/c1": () => ok(community()) });
    renderWithClient(<CommunityDetail />);

    await userEvent.click(await screen.findByRole("button", { name: "Deactivate" }));
    const dialog = screen.getByRole("dialog", { name: /deactivate java masters/i });
    await userEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === "PATCH")).toBe(false);
  });

  it("deactivates after confirming and shows the inactive label", async () => {
    let current = community();
    mockApi({
      "GET /communities/c1": () => ok(current),
      "PATCH /communities/c1/deactivate": () => {
        current = community({ is_active: false });
        return ok(current);
      },
    });
    renderWithClient(<CommunityDetail />);

    await userEvent.click(await screen.findByRole("button", { name: "Deactivate" }));
    const dialog = screen.getByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: "Deactivate" }));

    expect(await screen.findByText("Inactive")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Activate" })).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("closes the dialog on Escape", async () => {
    mockApi({ "GET /communities/c1": () => ok(community({ is_active: false })) });
    renderWithClient(<CommunityDetail />);

    await userEvent.click(await screen.findByRole("button", { name: "Activate" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows a not-found message", async () => {
    mockApi({ "GET /communities/c1": () => fail(404, "COMMUNITY_NOT_FOUND") });
    renderWithClient(<CommunityDetail />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/community not found/i);
  });
});
