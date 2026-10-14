"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { useAuth } from "@/lib/auth";

const NAV = [
  { href: "/app", label: "Communities" },
  { href: "/app/settings", label: "Settings" },
];

function isCurrent(href: string, pathname: string) {
  if (href === "/app") return pathname === "/app" || pathname.startsWith("/app/communities");
  return pathname.startsWith(href);
}

export function AppShell({ children }: { children: ReactNode }) {
  const { state, signOut } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (state === "anonymous") router.replace("/login");
  }, [state, router]);

  if (state !== "authenticated") {
    return (
      <div className="flex flex-1 items-center justify-center gap-2 text-ink-muted">
        <Spinner label="Checking your session" />
        <span>Checking your session…</span>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col md:flex-row">
      <aside className="flex shrink-0 flex-col gap-4 border-b border-line bg-surface p-4 md:w-56 md:border-r md:border-b-0">
        <Link href="/app" className="px-2 font-semibold">
          PulseAccess
        </Link>
        <nav aria-label="Main" className="flex gap-1 md:flex-col">
          {NAV.map((item) => {
            const current = isCurrent(item.href, pathname);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={current ? "page" : undefined}
                className={`rounded-[var(--radius-control)] px-2 py-1.5 text-[15px] ${
                  current ? "bg-accent-soft font-medium text-ink" : "text-ink-muted hover:bg-surface-sunken"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <div className="flex flex-1 flex-col">
        <header className="flex h-14 items-center justify-end border-b border-line px-6">
          <Button variant="secondary" size="sm" onClick={signOut}>
            Log out
          </Button>
        </header>
        <main id="main" className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
