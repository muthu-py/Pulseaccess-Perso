import Link from "next/link";
import type { ReactNode } from "react";

const buttonBase =
  "inline-flex h-10 items-center rounded-[var(--radius-control)] px-4 text-[15px] font-medium";

export function SiteHeader() {
  return (
    <header className="border-b border-line bg-surface">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-x-6 gap-y-2 px-6 py-3">
        <Link href="/" className="font-semibold">
          PulseAccess
        </Link>
        <nav aria-label="Main" className="flex flex-wrap items-center gap-x-5 gap-y-1 text-[15px]">
          <Link href="/how-it-works" className="text-ink-muted hover:text-ink">
            How it works
          </Link>
          <Link href="/telegram-bot" className="text-ink-muted hover:text-ink">
            The bot
          </Link>
          <Link href="/faq" className="text-ink-muted hover:text-ink">
            FAQ
          </Link>
          <Link href="/login" className="text-ink-muted hover:text-ink">
            Log in
          </Link>
          <Link href="/signup" className={`${buttonBase} bg-accent text-accent-ink hover:bg-accent-hover`}>
            Create an account
          </Link>
        </nav>
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="mt-auto border-t border-line bg-surface">
      <div className="mx-auto flex max-w-5xl flex-col gap-4 px-6 py-8 text-sm text-ink-muted sm:flex-row sm:justify-between">
        <p>PulseAccess</p>
        <nav aria-label="Footer" className="flex flex-wrap gap-x-5 gap-y-2">
          <Link href="/privacy" className="hover:text-ink">
            Privacy
          </Link>
          <Link href="/terms" className="hover:text-ink">
            Terms
          </Link>
          <Link href="/contact" className="hover:text-ink">
            Contact
          </Link>
          <Link href="/m/login" className="hover:text-ink">
            Member log in
          </Link>
        </nav>
      </div>
    </footer>
  );
}

/** Narrow reading column used by the text pages. */
export function Page({ title, intro, children }: { title: string; intro?: string; children: ReactNode }) {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-8 px-6 py-14">
      <div className="flex flex-col gap-3">
        <h1 className="text-4xl font-semibold tracking-tight text-balance">{title}</h1>
        {intro && <p className="text-lg text-ink-muted">{intro}</p>}
      </div>
      <div className="flex flex-col gap-8">{children}</div>
    </div>
  );
}

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-xl font-semibold">{title}</h2>
      <div className="flex flex-col gap-3 text-ink-muted [&_a]:text-accent [&_a]:underline [&_a]:underline-offset-4 [&_li]:ml-5 [&_li]:list-disc [&_strong]:font-medium [&_strong]:text-ink">
        {children}
      </div>
    </section>
  );
}

export function ButtonLink({ href, children, variant = "primary" }: { href: string; children: ReactNode; variant?: "primary" | "secondary" }) {
  return (
    <Link
      href={href}
      className={`${buttonBase} ${
        variant === "primary"
          ? "bg-accent text-accent-ink hover:bg-accent-hover"
          : "border border-line-strong bg-surface text-ink hover:bg-surface-sunken"
      }`}
    >
      {children}
    </Link>
  );
}
