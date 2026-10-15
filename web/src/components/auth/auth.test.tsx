import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AppShell } from "@/components/app/AppShell";
import { session } from "@/lib/api/client";
import { AuthProvider } from "@/lib/auth";

import { LoginForm } from "./LoginForm";
import { RESEND_SECONDS } from "./OtpStep";
import { SignupForm, validateSignup } from "./SignupForm";

const router = { push: vi.fn(), replace: vi.fn() };
let search = "";

vi.mock("next/navigation", () => ({
  useRouter: () => router,
  usePathname: () => "/app",
  useSearchParams: () => new URLSearchParams(search),
}));

function respond(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function wrap(ui: ReactNode) {
  const client = new QueryClient();
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>{ui}</AuthProvider>
    </QueryClientProvider>,
  );
}

/** Routes fetch by URL; the refresh call fails unless a test says otherwise. */
function mockApi(routes: Record<string, () => Response>) {
  const fetchMock = vi.fn<(url: string, init?: RequestInit) => Promise<Response>>(async (url) => {
    const handler = routes[url.replace("/api/v1", "")];
    return handler ? handler() : respond(401, { detail: "no session" });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

beforeEach(() => {
  router.push.mockReset();
  router.replace.mockReset();
  session.clear("creator");
  search = "";
});

describe("validateSignup", () => {
  const ok = { name: "Asha", username: "asha_k", email: "a@b.co", phone: "" };

  it("accepts a valid form with no phone", () => {
    expect(validateSignup(ok)).toEqual({});
  });

  it("flags a short or invalid username, bad email and phone without country code", () => {
    const errors = validateSignup({ ...ok, username: "a!", email: "nope", phone: "98765" });
    expect(errors.username).toBeDefined();
    expect(errors.email).toBeDefined();
    expect(errors.phone).toMatch(/country code/);
  });
});

describe("SignupForm", () => {
  it("shows field errors and does not call the API when invalid", async () => {
    const fetchMock = mockApi({});
    wrap(<SignupForm />);

    await userEvent.click(screen.getByRole("button", { name: /create account/i }));

    expect(screen.getByLabelText(/^Name/)).toHaveAccessibleDescription("Enter your name.");
    expect(fetchMock).toHaveBeenCalledTimes(1); // only the session-restore refresh
  });

  it("registers, sends the first code and opens login on the code step", async () => {
    const fetchMock = mockApi({
      "/auth/register": () => respond(201, { success: true, data: { creator: {} } }),
      "/auth/request-otp": () => respond(200, { success: true, data: { message: "sent" } }),
    });
    wrap(<SignupForm />);

    await userEvent.type(screen.getByLabelText(/^Name/), "Asha");
    await userEvent.type(screen.getByLabelText(/^Username/), "asha_k");
    await userEvent.type(screen.getByLabelText(/^Email/), "a@b.co");
    await userEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() =>
      expect(router.push).toHaveBeenCalledWith("/login?registered=1&sent=1&identifier=a%40b.co"),
    );
    const otpCall = fetchMock.mock.calls.find(([url]) => url === "/api/v1/auth/request-otp");
    expect(JSON.parse(String(otpCall?.[1]?.body))).toEqual({ identifier: "a@b.co" });
  });

  it("still goes to login if sending the first code fails", async () => {
    mockApi({
      "/auth/register": () => respond(201, { success: true, data: { creator: {} } }),
      "/auth/request-otp": () => respond(503, { detail: "down" }),
    });
    wrap(<SignupForm />);

    await userEvent.type(screen.getByLabelText(/^Name/), "Asha");
    await userEvent.type(screen.getByLabelText(/^Username/), "asha_k");
    await userEvent.type(screen.getByLabelText(/^Email/), "a@b.co");
    await userEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => expect(router.push).toHaveBeenCalledWith("/login?registered=1&identifier=a%40b.co"));
  });

  it("shows a friendly message when the account already exists", async () => {
    mockApi({
      "/auth/register": () => respond(409, { success: false, message: "dup", error_code: "CREATOR_ALREADY_EXISTS" }),
    });
    wrap(<SignupForm />);

    await userEvent.type(screen.getByLabelText(/^Name/), "Asha");
    await userEvent.type(screen.getByLabelText(/^Username/), "asha_k");
    await userEvent.type(screen.getByLabelText(/^Email/), "a@b.co");
    await userEvent.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/already exists/i);
  });
});

describe("LoginForm", () => {
  async function reachCodeStep() {
    await userEvent.type(await screen.findByLabelText(/email or username/i), "asha_k");
    await userEvent.click(screen.getByRole("button", { name: /send code/i }));
    await screen.findByLabelText(/6-digit code/i);
  }

  it("requests a code, shows the generic message, then logs in as soon as six digits are typed", async () => {
    mockApi({
      "/auth/request-otp": () => respond(200, { success: true, data: { message: "sent" } }),
      "/auth/verify-otp": () => respond(200, { success: true, data: { access_token: "tok", token_type: "bearer" } }),
    });
    wrap(<LoginForm />);

    await reachCodeStep();
    expect(screen.getByRole("status")).toHaveTextContent("If an account matches asha_k, we've sent it a 6-digit code.");

    await userEvent.type(screen.getByLabelText(/6-digit code/i), "123456");

    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/app"));
    expect(session.get()).toBe("tok");
  });

  it("opens on the code step right after signup", async () => {
    search = "registered=1&sent=1&identifier=a%40b.co";
    mockApi({});
    wrap(<LoginForm />);

    expect(await screen.findByLabelText(/6-digit code/i)).toHaveFocus();
    expect(screen.getByRole("status")).toHaveTextContent(/account created.*a@b\.co/i);
  });

  it("locks resending for a short while, then sends a new code", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      const fetchMock = mockApi({ "/auth/request-otp": () => respond(200, { success: true, data: {} }) });
      wrap(<LoginForm />);
      await reachCodeStep();

      const resend = screen.getByRole("button", { name: /send a new code in \d+s/i });
      expect(resend).toBeDisabled();

      // The countdown ticks once per render, so step the clock a second at a time.
      for (let i = 0; i < RESEND_SECONDS; i++) await act(() => vi.advanceTimersByTimeAsync(1000));
      const unlocked = await screen.findByRole("button", { name: /^send a new code$/i });
      await userEvent.click(unlocked);

      expect(await screen.findByText(/new code sent/i)).toBeInTheDocument();
      expect(fetchMock.mock.calls.filter(([url]) => url === "/api/v1/auth/request-otp")).toHaveLength(2);
    } finally {
      vi.useRealTimers();
    }
  });

  it.each([
    ["INVALID_OTP", 401, /isn't right/i],
    ["OTP_EXPIRED", 401, /expired/i],
    ["OTP_ATTEMPT_LIMIT_EXCEEDED", 429, /too many wrong attempts/i],
  ])("maps %s to a readable message", async (code, status, message) => {
    mockApi({
      "/auth/request-otp": () => respond(200, { success: true, data: {} }),
      "/auth/verify-otp": () => respond(status, { success: false, message: "x", error_code: code }),
    });
    wrap(<LoginForm />);

    await reachCodeStep();
    await userEvent.type(screen.getByLabelText(/6-digit code/i), "123456");

    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(session.get()).toBeNull();
  });

  it("rejects a code that isn't 6 digits without calling the API", async () => {
    const fetchMock = mockApi({ "/auth/request-otp": () => respond(200, { success: true, data: {} }) });
    wrap(<LoginForm />);

    await reachCodeStep();
    const callsBefore = fetchMock.mock.calls.length;
    await userEvent.type(screen.getByLabelText(/6-digit code/i), "123");
    await userEvent.click(screen.getByRole("button", { name: /^log in$/i }));

    expect(screen.getByLabelText(/6-digit code/i)).toHaveAccessibleDescription(/enter the 6-digit code/i);
    expect(fetchMock.mock.calls.length).toBe(callsBefore);
  });

  it("shows the rate-limit message when too many codes are requested", async () => {
    mockApi({ "/auth/request-otp": () => respond(429, { detail: "Too many requests" }) });
    wrap(<LoginForm />);

    await userEvent.type(await screen.findByLabelText(/email or username/i), "asha_k");
    await userEvent.click(screen.getByRole("button", { name: /send code/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/too many requests/i);
  });

  it("never skips the code when an old session exists: names the account and offers to switch", async () => {
    const fetchMock = mockApi({
      "/auth/refresh": () => respond(200, { success: true, data: { access_token: "t" } }),
      "/auth/me": () => respond(200, { success: true, data: { name: "Naveen", email: "naveen@example.com" } }),
      "/auth/logout": () => respond(200, { success: true, data: { message: "bye" } }),
    });
    wrap(<LoginForm />);

    expect(await screen.findByText("Naveen")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /continue to dashboard/i })).toHaveAttribute("href", "/app");
    expect(router.replace).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: /log out and use another account/i }));
    expect(await screen.findByLabelText(/email or username/i)).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([url]) => url === "/api/v1/auth/logout")).toBe(true);
    expect(session.get()).toBeNull();
  });
});

describe("AppShell", () => {
  it("redirects to /login when there is no session", async () => {
    mockApi({});
    wrap(
      <AppShell>
        <p>secret</p>
      </AppShell>,
    );

    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/login"));
    expect(screen.queryByText("secret")).not.toBeInTheDocument();
  });

  it("restores the session from the refresh cookie and logs out", async () => {
    const fetchMock = mockApi({
      "/auth/refresh": () => respond(200, { success: true, data: { access_token: "t" } }),
      "/auth/logout": () => respond(200, { success: true, data: { message: "bye" } }),
    });
    wrap(
      <AppShell>
        <p>secret</p>
      </AppShell>,
    );

    expect(await screen.findByText("secret")).toBeInTheDocument();
    // The shell has a mobile and a desktop Log out button; CSS shows one at a time.
    await userEvent.click(screen.getAllByRole("button", { name: /log out/i })[0]);

    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/login"));
    expect(fetchMock.mock.calls.some(([url]) => url === "/api/v1/auth/logout")).toBe(true);
    expect(session.get()).toBeNull();
  });
});
