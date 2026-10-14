/** Returns `value` if it is an in-app path, otherwise `fallback`. Stops open redirects via ?next=. */
export function safeNext(value: string | null | undefined, fallback: string): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.includes("\\")) return fallback;
  return value;
}
