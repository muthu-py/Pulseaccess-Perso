"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { Logo } from "@/components/ui/Brand";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { useMemberAuth } from "@/lib/member-auth";

/** Page frame for signed-in members. Sends signed-out visitors to login and brings them back after. */
export function MemberShell({ children }: { children: ReactNode }) {
  const { signedIn, signOut } = useMemberAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!signedIn) router.replace(`/m/login?next=${encodeURIComponent(pathname)}`);
  }, [signedIn, router, pathname]);

  if (!signedIn) {
    return (
      <div className="flex flex-1 items-center justify-center gap-2 text-ink-muted">
        <Spinner label="Redirecting to login" />
        <span>Redirecting to login…</span>
      </div>
    );
  }

  const links = [
    { href: "/m/subscriptions", label: "My subscriptions" },
    { href: "/m/connect-telegram", label: "Telegram" },
  ];

  return (
    <div className="flex flex-1 flex-col">
      <header className="sticky top-0 z-30 border-b border-line bg-canvas/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-between gap-x-6 gap-y-2 px-5 py-3 sm:px-8">
          <Logo href="/m/subscriptions" />
          <div className="flex items-center gap-1">
            <nav aria-label="Main" className="flex gap-1 text-[15px]">
              {links.map((l) => {
                const current = pathname.startsWith(l.href);
                return (
                  <Link
                    key={l.href}
                    href={l.href}
                    aria-current={current ? "page" : undefined}
                    className={`rounded-[var(--radius-control)] px-3 py-2 transition-colors ${
                      current ? "bg-accent-soft font-medium text-ink" : "text-ink-muted hover:bg-surface-sunken hover:text-ink"
                    }`}
                  >
                    {l.label}
                  </Link>
                );
              })}
            </nav>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                signOut();
                router.replace("/m/login");
              }}
            >
              Log out
            </Button>
          </div>
        </div>
      </header>
      <main id="main" className="mx-auto w-full max-w-4xl min-w-0 flex-1 px-5 py-10 sm:px-8">
        {children}
      </main>
    </div>
  );
}
