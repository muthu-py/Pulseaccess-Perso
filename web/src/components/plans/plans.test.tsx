import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { session } from "@/lib/api/client";

import { validatePlan } from "./PlanForm";
import { PlansSection } from "./PlansSection";

function respond(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}
const ok = (data: unknown) => respond(200, { success: true, data });
const fail = (status: number, code: string) => respond(status, { success: false, message: code, error_code: code });

const plan = (over: object = {}) => ({
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
  ...over,
});

type Handler = (init: RequestInit) => Response;

function mockApi(routes: Record<string, Handler>, status = "CONNECTED") {
  const fetchMock = vi.fn(async (url: string, init: RequestInit = {}) => {
    const key = `${init.method ?? "GET"} ${url.replace("/api/v1", "")}`;
    if (key === "GET /telegram/communities/c1/status") return ok({ status, telegram_chat_id: "-100" });
    const handler = routes[key];
    return handler ? handler(init) : respond(500, { detail: `unmocked ${key}` });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderSection() {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <PlansSection communityId="c1" />
    </QueryClientProvider>,
  );
}

const bodyOf = (fetchMock: ReturnType<typeof mockApi>, method: string) =>
  JSON.parse(fetchMock.mock.calls.find(([, init]) => init?.method === method)![1]!.body as string);

beforeEach(() => session.set("tok"));

describe("validatePlan", () => {
  const ok = { name: "Monthly", price: "499", duration: "30", description: "" };

  it("accepts valid values", () => expect(validatePlan(ok)).toEqual({}));

  it("rejects bad name, price and duration", () => {
    expect(validatePlan({ ...ok, name: "a" }).name).toBeDefined();
    expect(validatePlan({ ...ok, price: "0.50" }).price).toMatch(/between/);
    expect(validatePlan({ ...ok, price: "499.999" }).price).toBeDefined();
    expect(validatePlan({ ...ok, price: "abc" }).price).toBeDefined();
    expect(validatePlan({ ...ok, duration: "0" }).duration_days).toBeDefined();
    expect(validatePlan({ ...ok, duration: "3.5" }).duration_days).toBeDefined();
    expect(validatePlan({ ...ok, duration: "4000" }).duration_days).toBeDefined();
  });
});

describe("PlansSection", () => {
  it("lists plans with price, duration and a text status", async () => {
    mockApi({
      "GET /communities/c1/plans": () =>
        ok([plan(), plan({ id: "p2", name: "Yearly", price: "4999.00", duration_days: 365, is_active: false })]),
    });
    renderSection();

    const monthly = await screen.findByRole("listitem", { name: "Monthly" });
    expect(within(monthly).getByText("₹499")).toBeInTheDocument();
    expect(within(monthly).getByText("30 days")).toBeInTheDocument();
    expect(within(monthly).getByText("On sale")).toBeInTheDocument();
    const yearly = screen.getByRole("listitem", { name: "Yearly" });
    expect(within(yearly).getByText("₹4,999")).toBeInTheDocument();
    expect(within(yearly).getByText("Inactive")).toBeInTheDocument();
  });

  it("locks plan creation with an explanation until the group is connected", async () => {
    mockApi({ "GET /communities/c1/plans": () => ok([]) }, "NOT_CONNECTED");
    renderSection();

    expect(await screen.findByText(/connect the telegram group to create plans/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "New plan" })).toBeDisabled();
  });

  it("creates a plan with the price as a rupee string", async () => {
    let created = false;
    const fetchMock = mockApi({
      "GET /communities/c1/plans": () => ok(created ? [plan()] : []),
      "POST /communities/c1/plans": () => {
        created = true;
        return respond(201, { success: true, data: plan() });
      },
    });
    renderSection();

    await userEvent.click(await screen.findByRole("button", { name: "New plan" }));
    await userEvent.type(screen.getByLabelText(/plan name/i), "Monthly");
    await userEvent.type(screen.getByLabelText(/^price/i), "499");
    await userEvent.click(screen.getByRole("button", { name: /create plan/i }));

    expect(await screen.findByRole("listitem", { name: "Monthly" })).toBeInTheDocument();
    expect(bodyOf(fetchMock, "POST")).toEqual({ name: "Monthly", price: "499.00", duration_days: 30 });
    expect(screen.queryByRole("form")).not.toBeInTheDocument();
  });

  it("validates before calling the API", async () => {
    const fetchMock = mockApi({ "GET /communities/c1/plans": () => ok([]) });
    renderSection();

    await userEvent.click(await screen.findByRole("button", { name: "New plan" }));
    await userEvent.type(screen.getByLabelText(/plan name/i), "Monthly");
    await userEvent.type(screen.getByLabelText(/^price/i), "0");
    await userEvent.click(screen.getByRole("button", { name: /create plan/i }));

    expect(screen.getByLabelText(/^price/i)).toHaveAccessibleDescription(/between ₹1 and/i);
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === "POST")).toBe(false);
  });

  it("shows a duplicate-name error on the name field", async () => {
    mockApi({
      "GET /communities/c1/plans": () => ok([]),
      "POST /communities/c1/plans": () => fail(409, "DUPLICATE_PLAN_NAME"),
    });
    renderSection();

    await userEvent.click(await screen.findByRole("button", { name: "New plan" }));
    await userEvent.type(screen.getByLabelText(/plan name/i), "Monthly");
    await userEvent.type(screen.getByLabelText(/^price/i), "499");
    await userEvent.click(screen.getByRole("button", { name: /create plan/i }));

    expect(await screen.findByText(/already has a plan with this name/i)).toBeInTheDocument();
  });

  it("edits a plan, prefilled", async () => {
    const fetchMock = mockApi({
      "GET /communities/c1/plans": () => ok([plan()]),
      "PATCH /plans/p1": () => ok(plan({ price: "599.00" })),
    });
    renderSection();

    await userEvent.click(await screen.findByRole("button", { name: "Edit Monthly" }));
    const price = screen.getByLabelText(/^price/i);
    expect(price).toHaveValue("499.00");
    await userEvent.clear(price);
    await userEvent.type(price, "599");
    await userEvent.click(screen.getByRole("button", { name: /save changes/i }));

    await screen.findByRole("button", { name: "Edit Monthly" });
    expect(bodyOf(fetchMock, "PATCH")).toEqual({ name: "Monthly", description: null, price: "599.00", duration_days: 30 });
  });

  it("deactivates and activates a plan", async () => {
    let active = true;
    const fetchMock = mockApi({
      "GET /communities/c1/plans": () => ok([plan({ is_active: active })]),
      "PATCH /plans/p1/deactivate": () => {
        active = false;
        return ok(plan({ is_active: false }));
      },
      "PATCH /plans/p1/activate": () => {
        active = true;
        return ok(plan());
      },
    });
    renderSection();

    await userEvent.click(await screen.findByRole("button", { name: "Deactivate Monthly" }));
    // Deactivating takes a plan off sale, so it asks first
    const dialog = screen.getByRole("dialog", { name: /deactivate monthly/i });
    await userEvent.click(within(dialog).getByRole("button", { name: "Deactivate" }));
    expect(await screen.findByText("Inactive")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Activate Monthly" }));
    expect(await screen.findByText("On sale")).toBeInTheDocument();
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "PATCH")).toHaveLength(2);
  });
});
