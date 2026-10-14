import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { session } from "@/lib/api/client";

import { ConnectionPanel } from "./ConnectionPanel";

function respond(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}
const ok = (data: unknown) => respond(200, { success: true, data });

function renderPanel() {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <ConnectionPanel communityId="c1" />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  session.set("tok");
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllEnvs();
});

describe("ConnectionPanel", () => {
  it("shows setup steps and a waiting message while not connected", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ok({ status: "NOT_CONNECTED" })));
    renderPanel();

    expect(await screen.findByText("Not connected")).toBeInTheDocument();
    expect(screen.getByText(/invite users via link/i)).toBeInTheDocument();
    expect(screen.getByText(/ban users/i)).toBeInTheDocument();
    expect(screen.getByText(/waiting for the bot to be added/i)).toBeInTheDocument();
  });

  it("names the bot when NEXT_PUBLIC_TELEGRAM_BOT_USERNAME is set", async () => {
    vi.stubEnv("NEXT_PUBLIC_TELEGRAM_BOT_USERNAME", "@PulseAccessBot");
    vi.stubGlobal("fetch", vi.fn(async () => ok({ status: "NOT_CONNECTED" })));
    renderPanel();

    expect(await screen.findByText("@PulseAccessBot")).toBeInTheDocument();
  });

  it("falls back to a generic bot name when the username isn't configured", async () => {
    vi.stubEnv("NEXT_PUBLIC_TELEGRAM_BOT_USERNAME", "");
    vi.stubGlobal("fetch", vi.fn(async () => ok({ status: "NOT_CONNECTED" })));
    renderPanel();

    expect((await screen.findAllByText(/the PulseAccess bot/)).length).toBeGreaterThan(0);
  });

  it("shows the chat ID in mono and the date once connected, with no setup steps", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ok({ status: "CONNECTED", telegram_chat_id: "-1001234567890", connected_at: "2026-10-10T10:00:00Z" })),
    );
    renderPanel();

    const id = await screen.findByText("-1001234567890");
    expect(id).toHaveClass("font-mono");
    expect(screen.getAllByText("Connected")).toHaveLength(2); // badge + date row label
    expect(screen.queryByText(/waiting for the bot/i)).not.toBeInTheDocument();
  });

  it("explains what to fix when attention is needed", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ok({ status: "NEEDS_ATTENTION", telegram_chat_id: "-100" })));
    renderPanel();

    expect(await screen.findByText("Needs attention")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/can't manage this group/i);
    expect(screen.getByText(/invite users via link/i)).toBeInTheDocument();
  });

  it("keeps polling and flips to Connected when the backend reports it", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(async () => ok({ status: "NOT_CONNECTED" }))
      .mockImplementation(async () => ok({ status: "CONNECTED", telegram_chat_id: "-100999", connected_at: null }));
    vi.stubGlobal("fetch", fetchMock);
    renderPanel();

    await screen.findByText(/waiting for the bot to be added/i);
    await act(() => vi.advanceTimersByTimeAsync(4100));

    expect(await screen.findByText("-100999")).toBeInTheDocument();
    expect(screen.queryByText(/waiting for the bot/i)).not.toBeInTheDocument();

    const callsAfterConnect = fetchMock.mock.calls.length;
    await act(() => vi.advanceTimersByTimeAsync(12000));
    expect(fetchMock.mock.calls.length).toBe(callsAfterConnect); // polling stops
  });

  it("shows an error if the status can't be loaded", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => respond(500, { detail: "boom" })));
    renderPanel();

    expect(await screen.findByRole("alert")).toHaveTextContent(/couldn't check the connection/i);
  });
});
