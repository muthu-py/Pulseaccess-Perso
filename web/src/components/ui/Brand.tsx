import Link from "next/link";

/** The mark: a pass with a live dot cut into it. */
export function LogoMark({ className = "size-7" }: { className?: string }) {
  return (
    <svg viewBox="0 0 28 28" className={className} aria-hidden="true" focusable="false">
      <rect x="2" y="6" width="24" height="16" rx="4" fill="var(--pass)" />
      <circle cx="2" cy="14" r="3" fill="var(--canvas)" />
      <circle cx="26" cy="14" r="3" fill="var(--canvas)" />
      <circle cx="14" cy="14" r="3.25" fill="var(--pass-ink)" />
    </svg>
  );
}

export function Logo({ href = "/", tone = "ink" }: { href?: string; tone?: "ink" | "night" }) {
  return (
    <Link
      href={href}
      translate="no"
      className={`inline-flex items-center gap-2 font-display text-lg font-semibold tracking-[-0.02em] ${
        tone === "night" ? "text-night-ink" : "text-ink"
      }`}
    >
      <LogoMark />
      PulseAccess
    </Link>
  );
}

/** Live indicator for states that update by themselves (waiting on Telegram or Razorpay). */
export function Pulse({ children, tone = "accent" }: { children: React.ReactNode; tone?: "accent" | "warning" }) {
  return (
    <p role="status" aria-live="polite" className="flex items-center gap-2.5 text-sm text-ink-muted">
      <span className={`pulse-dot ${tone === "accent" ? "text-accent" : "text-warning"}`} aria-hidden="true" />
      <span>{children}</span>
    </p>
  );
}
