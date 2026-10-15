import { ApiError } from "@/lib/api/client";

/** Message for any failed request; `overrides` maps backend error codes to friendlier text. */
export function errorText(err: unknown, overrides: Record<string, string> = {}): string {
  if (err instanceof ApiError) {
    return overrides[err.code] ?? (err.status >= 500 ? "Something went wrong on our side. Try again." : err.message);
  }
  return "Something went wrong. Try again.";
}
