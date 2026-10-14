import { apiRequest } from "@/lib/api/client";

/** Requests a login code right after signup. Returns false instead of throwing: the account exists either way. */
export async function sendLoginCode(path: "/auth/request-otp" | "/members/request-otp", body: Record<string, string>) {
  try {
    await apiRequest(path, { method: "POST", auth: null, body });
    return true;
  } catch {
    return false;
  }
}
