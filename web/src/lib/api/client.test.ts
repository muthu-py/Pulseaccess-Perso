import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiRequest, session } from "./client";

function respond(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

beforeEach(() => {
  session.clear("creator");
  session.clear("member");
});
afterEach(() => vi.unstubAllGlobals());

describe("apiRequest", () => {
  it("unwraps the success envelope and sends the bearer token", async () => {
    const fetchMock = vi.fn().mockResolvedValue(respond(200, { success: true, data: { id: 1 } }));
    vi.stubGlobal("fetch", fetchMock);
    session.set("tok");

    await expect(apiRequest("/things")).resolves.toEqual({ id: 1 });
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe("Bearer tok");
  });

  it("maps domain errors to ApiError.code", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(respond(401, { success: false, message: "bad", error_code: "INVALID_OTP" })));
    await expect(apiRequest("/x", { auth: null })).rejects.toMatchObject({ code: "INVALID_OTP", status: 401 });
  });

  it("maps HTTPException detail strings", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(respond(429, { detail: "slow down" })));
    await expect(apiRequest("/x", { auth: null })).rejects.toMatchObject({ code: "HTTP_429", message: "slow down" });
  });

  it("maps 422 validation errors to fields", async () => {
    const detail = [{ loc: ["body", "phone"], msg: "Value error, Phone must include the country code" }];
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(respond(422, { detail })));
    const err = (await apiRequest("/x", { auth: null }).catch((e) => e)) as ApiError;
    expect(err).toBeInstanceOf(ApiError);
    expect(err.fields.phone).toBe("Phone must include the country code");
  });

  it("reports network failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("failed")));
    await expect(apiRequest("/x", { auth: null })).rejects.toMatchObject({ code: "NETWORK_ERROR" });
  });

  it("refreshes once on 401 for creators and retries", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(respond(401, { detail: "expired" }))
      .mockResolvedValueOnce(respond(200, { success: true, data: { access_token: "new" } }))
      .mockResolvedValueOnce(respond(200, { success: true, data: "ok" }));
    vi.stubGlobal("fetch", fetchMock);
    session.set("old");

    await expect(apiRequest("/secure")).resolves.toBe("ok");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/v1/auth/refresh");
    expect(fetchMock.mock.calls[2][1].headers.Authorization).toBe("Bearer new");
    expect(session.get()).toBe("new");
  });

  it("does not refresh for members", async () => {
    const fetchMock = vi.fn().mockResolvedValue(respond(401, { detail: "expired" }));
    vi.stubGlobal("fetch", fetchMock);
    session.set("m", "member");

    await expect(apiRequest("/members/me", { auth: "member" })).rejects.toMatchObject({ status: 401 });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
