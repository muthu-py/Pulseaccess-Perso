/**
 * Fetch wrapper for the PulseAccess API (proxied at /api/v1).
 *
 * - Unwraps `{ success: true, data }` envelopes.
 * - Turns every failure into an `ApiError` with a stable `code`.
 * - Creator access tokens live in memory only and are silently refreshed through
 *   the HttpOnly cookie on 401.
 * - Members have no refresh endpoint, so their short-lived token is also kept in
 *   localStorage until it expires. Otherwise every reload, and the return from a
 *   Razorpay tab, would log them out.
 */

export const API_BASE = "/api/v1";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  /** Field-level messages from 422 validation errors, keyed by field name. */
  readonly fields: Record<string, string>;

  constructor(
    message: string,
    opts: { status: number; code: string; fields?: Record<string, string> },
  ) {
    super(message);
    this.name = "ApiError";
    this.status = opts.status;
    this.code = opts.code;
    this.fields = opts.fields ?? {};
  }
}

type Role = "creator" | "member";

const tokens: Record<Role, string | null> = { creator: null, member: null };

/** localStorage key for the member token. */
export const MEMBER_TOKEN_KEY = "pulseaccess.member_token";

/** When a JWT expires, in ms since epoch. Null if it can't be read. */
export function tokenExpiry(token: string): number | null {
  try {
    const payload = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const exp = (JSON.parse(atob(payload)) as { exp?: unknown }).exp;
    return typeof exp === "number" ? exp * 1000 : null;
  } catch {
    return null;
  }
}

function isExpired(token: string): boolean {
  const exp = tokenExpiry(token);
  return exp !== null && exp <= Date.now();
}

// Storage can be missing (server render) or throw (private mode, blocked site data).
const stored = {
  read(): string | null {
    try {
      return typeof window === "undefined" ? null : window.localStorage.getItem(MEMBER_TOKEN_KEY);
    } catch {
      return null;
    }
  },
  write(token: string | null) {
    try {
      if (typeof window === "undefined") return;
      if (token) window.localStorage.setItem(MEMBER_TOKEN_KEY, token);
      else window.localStorage.removeItem(MEMBER_TOKEN_KEY);
    } catch {
      // Memory still holds the token for this page.
    }
  },
};

const memberTokenListeners = new Set<() => void>();
const notifyMemberToken = () => memberTokenListeners.forEach((listener) => listener());

export const session = {
  get: (role: Role = "creator") => {
    if (role === "member") {
      tokens.member ??= stored.read();
      // Treat an expired token as gone. The provider's expiry timer clears storage.
      if (tokens.member && isExpired(tokens.member)) return null;
    }
    return tokens[role];
  },
  set: (token: string | null, role: Role = "creator") => {
    tokens[role] = token;
    if (role === "member") {
      stored.write(token);
      notifyMemberToken();
    }
  },
  clear: (role: Role = "creator") => session.set(null, role),
};

/**
 * Subscribe to member token changes, including logins and logouts in other tabs.
 * Shaped for `useSyncExternalStore`.
 */
export function subscribeMemberToken(listener: () => void): () => void {
  memberTokenListeners.add(listener);
  function onStorage(e: StorageEvent) {
    if (e.key !== MEMBER_TOKEN_KEY && e.key !== null) return;
    tokens.member = stored.read();
    listener();
  }
  window.addEventListener("storage", onStorage);
  return () => {
    memberTokenListeners.delete(listener);
    window.removeEventListener("storage", onStorage);
  };
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  /** Which token to send. `null` sends none (login, register). Default: creator. */
  auth?: Role | null;
};

type Json = Record<string, unknown> | undefined;

function toApiError(status: number, payload: Json): ApiError {
  if (payload && payload.success === false && typeof payload.error_code === "string") {
    return new ApiError(String(payload.message ?? "Request failed"), {
      status,
      code: payload.error_code,
    });
  }
  const detail = payload?.detail;
  if (Array.isArray(detail)) {
    const fields: Record<string, string> = {};
    for (const item of detail as { loc?: unknown[]; msg?: string }[]) {
      const name = String(item.loc?.[item.loc.length - 1] ?? "");
      if (name && !(name in fields)) {
        fields[name] = (item.msg ?? "Invalid value").replace(/^Value error, /, "");
      }
    }
    return new ApiError("Some fields need fixing.", { status, code: `HTTP_${status}`, fields });
  }
  return new ApiError(typeof detail === "string" ? detail : "Request failed", {
    status,
    code: `HTTP_${status}`,
  });
}

async function send(path: string, opts: RequestOptions, token: string | null) {
  const headers: Record<string, string> = {};
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;
  try {
    return await fetch(`${API_BASE}${path}`, {
      method: opts.method ?? "GET",
      headers,
      body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
      credentials: "same-origin",
    });
  } catch {
    throw new ApiError("Can't reach the server. Check your connection and try again.", {
      status: 0,
      code: "NETWORK_ERROR",
    });
  }
}

let refreshing: Promise<string | null> | null = null;

/** Exchanges the refresh cookie for a new creator access token. Single-flight. */
export function refreshCreatorSession(): Promise<string | null> {
  refreshing ??= (async () => {
    try {
      const res = await send("/auth/refresh", { method: "POST" }, null);
      if (!res.ok) return null;
      const payload = (await res.json()) as { data?: { access_token?: string } };
      const token = payload.data?.access_token ?? null;
      session.set(token, "creator");
      return token;
    } catch {
      return null;
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}

export async function apiRequest<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const role = opts.auth === undefined ? "creator" : opts.auth;
  let res = await send(path, opts, role ? session.get(role) : null);

  if (res.status === 401 && role === "creator" && path !== "/auth/refresh") {
    const fresh = await refreshCreatorSession();
    if (fresh) res = await send(path, opts, fresh);
  }

  let payload: Json;
  try {
    payload = (await res.json()) as Json;
  } catch {
    payload = undefined;
  }

  // Members can't refresh: a rejected token means logging in again. Clearing it
  // notifies the member provider, which sends the shell back to login.
  if (res.status === 401 && role === "member" && session.get("member")) session.clear("member");

  if (!res.ok) throw toApiError(res.status, payload);
  return (payload && "data" in payload ? payload.data : payload) as T;
}
