import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MEMBER_TOKEN_KEY, session } from "@/lib/api/client";
import { useMe } from "@/lib/member";
import { MemberAuthProvider } from "@/lib/member-auth";
import { safeNext } from "@/lib/safe-next";

import { ConnectTelegram } from "./ConnectTelegram";
import { MemberLoginForm } from "./MemberLoginForm";
import { MemberShell } from "./MemberShell";
import { MemberSignupForm, validateMemberSignup } from "./MemberSignupForm";

const router = { push: vi.fn(), replace: vi.fn() };
let search = "";
vi.mock("next/navigation", () => ({
  useRouter: () => router,
  usePathname: () => "/c/c1",
  useSearchParams: () => new URLSearchParams(search),
}));

/** A JWT-shaped token whose payload expires at `expMs`. The signature isn't checked client-side. */
function jwt(expMs: number) {
  const payload = btoa(JSON.stringify({ sub: "m1", exp: Math.floor(expMs / 1000) })).replace(/=+$/, "");
  return `h.${payload}.s`;
}

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

function wrap(ui: ReactNode) {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemberAuthProvider>{ui}</MemberAuthProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  router.push.mockReset();
  router.replace.mockReset();
  session.clear("member");
  search = "";
});

describe("safeNext", () => {
  it("allows in-app paths only", () => {
    expect(safeNext("/c/abc", "/x")).toBe("/c/abc");
    expect(safeNext("https://evil.example", "/x")).toBe("/x");
    expect(safeNext("//evil.example", "/x")).toBe("/x");
    expect(safeNext("/\\evil.example", "/x")).toBe("/x");
    expect(safeNext(null, "/x")).toBe("/x");
  });
});

describe("validateMemberSignup", () => {
  it("requires name, email and a phone with country code", () => {
    const errors = validateMemberSignup({ name: "", email: "x", phone: "98765" });
    expect(Object.keys(errors).sort()).toEqual(["email", "name", "phone"]);
    expect(validateMemberSignup({ name: "Ravi", email: "r@x.co", phone: "+919876543210" })).toEqual({});
  });
});

describe("MemberSignupForm", () => {
  it("registers, sends the first code and goes to member login, keeping next", async () => {
    search = "next=%2Fc%2Fc1";
    mockApi({
      "POST /members/register": () => respond(201, { success: true, data: {} }),
      "POST /members/request-otp": () => ok({ message: "sent" }),
    });
    wrap(<MemberSignupForm />);

    await userEvent.type(screen.getByLabelText(/^Name/), "Ravi");
    await userEvent.type(screen.getByLabelText(/^Email/), "r@x.co");
    await userEvent.type(screen.getByLabelText(/^Phone/), "+919876543210");
    await userEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() =>
      expect(router.push).toHaveBeenCalledWith("/m/login?registered=1&sent=1&identifier=r%40x.co&next=%2Fc%2Fc1"),
    );
  });

  it("explains an existing account", async () => {
    mockApi({ "POST /members/register": () => fail(409, "MEMBER_ALREADY_EXISTS") });
    wrap(<MemberSignupForm />);

    await userEvent.type(screen.getByLabelText(/^Name/), "Ravi");
    await userEvent.type(screen.getByLabelText(/^Email/), "r@x.co");
    await userEvent.type(screen.getByLabelText(/^Phone/), "+919876543210");
    await userEvent.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/already exists/i);
  });
});

describe("MemberLoginForm", () => {
  it("logs in with an email code and returns to the page they came from", async () => {
    search = "next=%2Fc%2Fc1";
    mockApi({
      "POST /members/request-otp": () => ok({ message: "sent" }),
      "POST /members/verify-otp": () => ok({ access_token: "mtok", token_type: "bearer" }),
    });
    wrap(<MemberLoginForm />);

    await userEvent.type(screen.getByLabelText(/^Email/), "r@x.co");
    await userEvent.click(screen.getByRole("button", { name: /send code/i }));
    await userEvent.type(await screen.findByLabelText(/6-digit code/i), "123456");

    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/c/c1"));
    expect(session.get("member")).toBe("mtok");
    expect(session.get("creator")).toBeNull();
    // Kept across reloads: members have no refresh cookie.
    expect(localStorage.getItem(MEMBER_TOKEN_KEY)).toBe("mtok");
  });

  it("opens on the code step right after signup", async () => {
    search = "registered=1&sent=1&identifier=r%40x.co";
    mockApi({});
    wrap(<MemberLoginForm />);

    expect(await screen.findByLabelText(/6-digit code/i)).toHaveFocus();
    expect(screen.getByRole("status")).toHaveTextContent(/account created.*r@x\.co/i);
  });

  it("never skips the code when a saved token exists: names the account and offers to switch", async () => {
    search = "next=%2Fm%2Fpayments%2Fp1";
    localStorage.setItem(MEMBER_TOKEN_KEY, jwt(Date.now() + 60_000));
    mockApi({ "GET /members/me": () => ok({ id: "m1", name: "Naveen", email: "naveen@example.com" }) });
    wrap(<MemberLoginForm />);

    expect(await screen.findByText("Naveen")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /^continue$/i })).toHaveAttribute("href", "/m/payments/p1");
    expect(router.replace).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: /log out and use another account/i }));
    expect(await screen.findByLabelText(/^Email/)).toBeInTheDocument();
    expect(localStorage.getItem(MEMBER_TOKEN_KEY)).toBeNull();
  });

  it("ignores an off-site next and shows readable OTP errors", async () => {
    search = "next=https%3A%2F%2Fevil.example";
    mockApi({
      "POST /members/request-otp": () => ok({ message: "sent" }),
      "POST /members/verify-otp": () => fail(401, "OTP_EXPIRED"),
    });
    wrap(<MemberLoginForm />);

    await userEvent.type(screen.getByLabelText(/^Email/), "r@x.co");
    await userEvent.click(screen.getByRole("button", { name: /send code/i }));
    await userEvent.type(await screen.findByLabelText(/6-digit code/i), "123456");

    expect(await screen.findByRole("alert")).toHaveTextContent(/expired/i);
    expect(router.replace).not.toHaveBeenCalled();
  });
});

describe("MemberShell", () => {
  it("redirects signed-out visitors to login with the page to return to", async () => {
    wrap(
      <MemberShell>
        <p>plans</p>
      </MemberShell>,
    );
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/m/login?next=%2Fc%2Fc1"));
    expect(screen.queryByText("plans")).not.toBeInTheDocument();
  });

  it("shows content and logs out", async () => {
    session.set("mtok", "member");
    wrap(
      <MemberShell>
        <p>plans</p>
      </MemberShell>,
    );
    expect(await screen.findByText("plans")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /log out/i }));
    expect(session.get("member")).toBeNull();
    expect(localStorage.getItem(MEMBER_TOKEN_KEY)).toBeNull();
    expect(router.replace).toHaveBeenCalledWith("/m/login");
  });

  it("restores a saved session after a reload", async () => {
    localStorage.setItem(MEMBER_TOKEN_KEY, jwt(Date.now() + 60_000));
    wrap(
      <MemberShell>
        <p>plans</p>
      </MemberShell>,
    );
    expect(await screen.findByText("plans")).toBeInTheDocument();
    expect(router.replace).not.toHaveBeenCalled();
  });

  it("ignores a saved token that has expired", async () => {
    localStorage.setItem(MEMBER_TOKEN_KEY, jwt(Date.now() - 1000));
    wrap(
      <MemberShell>
        <p>plans</p>
      </MemberShell>,
    );
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/m/login?next=%2Fc%2Fc1"));
    expect(screen.queryByText("plans")).not.toBeInTheDocument();
  });

  it("logs out when the token expires while the page is open", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      session.set(jwt(Date.now() + 5_000), "member");
      wrap(
        <MemberShell>
          <p>plans</p>
        </MemberShell>,
      );
      expect(await screen.findByText("plans")).toBeInTheDocument();

      await act(() => vi.advanceTimersByTimeAsync(5_000));
      await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/m/login?next=%2Fc%2Fc1"));
      expect(localStorage.getItem(MEMBER_TOKEN_KEY)).toBeNull();
    } finally {
      vi.useRealTimers();
    }
  });
});

describe("expired member token", () => {
  it("sends the member back to login with the page to return to", async () => {
    session.set("old", "member");
    mockApi({ "GET /members/me": () => respond(401, { detail: "Token expired" }) });
    function Probe() {
      useMe();
      return <p>content</p>;
    }
    wrap(
      <MemberShell>
        <Probe />
      </MemberShell>,
    );

    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/m/login?next=%2Fc%2Fc1"));
    expect(session.get("member")).toBeNull();
  });
});

describe("ConnectTelegram", () => {
  beforeEach(() => session.set("mtok", "member"));

  it("shows the bot link and the phone that must match", async () => {
    mockApi({
      "GET /telegram/connect/member": () => ok({ connected: false }),
      "GET /members/me": () => ok({ id: "m1", name: "Ravi", phone: "+919876543210", email: "r@x.co", is_active: true, telegram_connected: false }),
      "POST /telegram/connect/member": () =>
        ok({ telegram_link: "https://t.me/bot?start=m", expires_at: new Date(Date.now() + 600000).toISOString() }),
    });
    wrap(<ConnectTelegram />);

    expect(await screen.findByText("+919876543210")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /connect telegram/i }));
    expect(await screen.findByRole("link", { name: /open telegram/i })).toHaveAttribute("href", "https://t.me/bot?start=m");
  });

  it("shows connected state with a continue link when next is set", async () => {
    search = "next=%2Fc%2Fc1";
    mockApi({
      "GET /telegram/connect/member": () => ok({ connected: true, telegram_username: "ravi" }),
      "GET /members/me": () => ok({ id: "m1", phone: "+91" }),
    });
    wrap(<ConnectTelegram />);

    expect(await screen.findByText("@ravi")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Continue" })).toHaveAttribute("href", "/c/c1");
  });
});
