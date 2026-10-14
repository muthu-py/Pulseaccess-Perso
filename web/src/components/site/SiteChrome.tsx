import Link from "next/link";
import type { ReactNode } from "react";

import { buttonClass } from "@/components/ui/Button";
import { Logo } from "@/components/ui/Brand";

const NAV = [
  { href: "/how-it-works", label: "How it works" },
  { href: "/telegram-bot", label: "The bot" },
  { href: "/faq", label: "FAQ" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-line/70 bg-canvas/85 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-x-4 px-4 py-3 sm:px-8">
        <Logo />
        <nav aria-label="Main" className="flex flex-wrap items-center gap-x-1 gap-y-1 text-[15px]">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="hidden rounded-[var(--radius-control)] px-3 py-2 text-ink-muted transition-colors hover:bg-surface-sunken hover:text-ink sm:inline-flex"
            >
              {item.label}
            </Link>
          ))}
          <Link
            href="/login"
            className="rounded-[var(--radius-control)] px-3 py-2 text-ink-muted transition-colors hover:bg-surface-sunken hover:text-ink"
          >
            Log in
          </Link>
          <Link href="/signup" className={buttonClass("primary", "md", "ml-1")}>
            <span className="sm:hidden">Sign up</span>
            <span className="hidden sm:inline">Create an account</span>
          </Link>
        </nav>
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="mt-auto border-t border-line">
      <div className="mx-auto grid max-w-6xl gap-8 px-5 py-12 sm:px-8 md:grid-cols-[1.4fr_1fr_1fr_1fr]">
        <div className="flex flex-col gap-3">
          <Logo />
          <p className="max-w-xs text-sm text-ink-muted">
            Plans, Razorpay payments and subscriptions for paid Telegram communities.
          </p>
        </div>
        <FooterColumn
          title="Product"
          links={[
            ["/how-it-works", "How it works"],
            ["/telegram-bot", "The Telegram bot"],
            ["/faq", "FAQ"],
          ]}
        />
        <FooterColumn
          title="Accounts"
          links={[
            ["/signup", "Create a creator account"],
            ["/login", "Creator log in"],
            ["/m/login", "Member log in"],
          ]}
        />
        <FooterColumn
          title="Company"
          links={[
            ["/privacy", "Privacy"],
            ["/terms", "Terms"],
            ["/contact", "Contact"],
          ]}
        />
      </div>
    </footer>
  );
}

function FooterColumn({ title, links }: { title: string; links: [string, string][] }) {
  return (
    <nav aria-label={title} className="flex flex-col gap-2.5 text-sm">
      <h2 className="font-sans text-sm font-medium text-ink">{title}</h2>
      {links.map(([href, label]) => (
        <Link key={href} href={href} className="w-fit text-ink-muted transition-colors hover:text-ink">
          {label}
        </Link>
      ))}
    </nav>
  );
}

/** Reading column for the text pages. */
export function Page({ title, intro, children }: { title: string; intro?: string; children: ReactNode }) {
  return (
    <div className="mx-auto grid w-full max-w-6xl gap-10 px-5 py-16 sm:px-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)] lg:gap-16 lg:py-24">
      <div className="flex flex-col gap-4 lg:sticky lg:top-28 lg:self-start">
        <h1 className="text-4xl font-semibold leading-[1.05] sm:text-5xl">{title}</h1>
        {intro && <p className="max-w-md text-lg text-ink-muted">{intro}</p>}
      </div>
      <div className="flex min-w-0 max-w-[68ch] flex-col gap-12">{children}</div>
    </div>
  );
}

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-2xl font-semibold">{title}</h2>
      <div className="flex flex-col gap-4 text-[17px] leading-relaxed text-ink-muted [&_a]:text-accent [&_a]:underline [&_a]:underline-offset-4 [&_a:hover]:text-accent-hover [&_li]:ml-5 [&_li]:pl-1 [&_ol]:list-decimal [&_ol_li]:marker:font-medium [&_ol_li]:marker:text-ink [&_strong]:font-medium [&_strong]:text-ink [&_ul]:list-disc">
        {children}
      </div>
    </section>
  );
}

export function ButtonLink({
  href,
  children,
  variant = "primary",
  size = "md",
}: {
  href: string;
  children: ReactNode;
  variant?: "primary" | "secondary";
  size?: "md" | "lg";
}) {
  return (
    <Link href={href} className={buttonClass(variant, size)}>
      {children}
    </Link>
  );
}
