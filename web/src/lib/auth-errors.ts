import { ApiError } from "@/lib/api/client";

/** Plain-language messages for the auth error codes the backend returns. */
const MESSAGES: Record<string, string> = {
  INVALID_OTP: "That code isn't right. Check the email and try again.",
  OTP_EXPIRED: "That code has expired. Request a new one.",
  OTP_ATTEMPT_LIMIT_EXCEEDED: "Too many wrong attempts. Request a new code.",
  INACTIVE_CREATOR: "This account is inactive. Contact support to reactivate it.",
  CREATOR_ALREADY_EXISTS: "An account with this email, username or phone already exists. Try logging in.",
  MEMBER_ALREADY_EXISTS: "An account with this email or phone already exists. Try logging in.",
  INACTIVE_MEMBER: "This account is inactive. Contact support to reactivate it.",
  HTTP_429: "Too many requests. Wait a few minutes and try again.",
  NETWORK_ERROR: "Can't reach the server. Check your connection and try again.",
};

export function authErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (MESSAGES[error.code]) return MESSAGES[error.code];
    return error.status >= 500 ? "Something went wrong on our side. Try again." : error.message;
  }
  return "Something went wrong. Try again.";
}
