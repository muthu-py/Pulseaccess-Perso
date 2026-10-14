"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { Logo } from "@/components/ui/Brand";
import { Spinner } from "@/components/ui/Spinner";
import { useAuth } from "@/lib/auth";

const NAV = [
  { href: "/app", label: "Communities", icon: CommunitiesIcon },
  { href: "/app/settings", label: "Settings", icon: SettingsIcon },
];

function isCurrent(href: string, pathname: string) {
  if (href === "/app") return pathname === "/app" || pathname.startsWith("/app/communities") || pathname === "/app/onboarding";
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
      <aside className="flex shrink-0 flex-col gap-2 border-b border-line bg-surface md:sticky md:top-0 md:h-dvh md:w-60 md:border-r md:border-b-0">
        <div className="flex items-center justify-between px-5 pt-4 pb-2 md:pt-6 md:pb-4">
          <Logo href="/app" />
          <button
            type="button"
            onClick={signOut}
            className="rounded-[var(--radius-control)] px-2.5 py-1.5 text-sm text-ink-muted transition-colors hover:bg-surface-sunken hover:text-ink md:hidden"
          >
            Log out
          </button>
        </div>
        <nav aria-label="Main" className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-col md:pb-0">
          {NAV.map((item) => {
            const current = isCurrent(item.href, pathname);
            const ItemIcon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={current ? "page" : undefined}
                className={`flex items-center gap-2.5 rounded-[var(--radius-control)] px-3 py-2 text-[15px] transition-colors ${
                  current ? "bg-accent-soft font-medium text-ink" : "text-ink-muted hover:bg-surface-sunken hover:text-ink"
                }`}
              >
                <ItemIcon active={current} />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="mt-auto hidden border-t border-line p-3 md:block">
          <button
            type="button"
            onClick={signOut}
            className="flex w-full items-center gap-2.5 rounded-[var(--radius-control)] px-3 py-2 text-left text-[15px] text-ink-muted transition-colors hover:bg-surface-sunken hover:text-ink"
          >
            <LogoutIcon />
            Log out
          </button>
        </div>
      </aside>
      <main id="main" className="min-w-0 flex-1 px-5 py-8 sm:px-10 md:py-12">
        <div className="mx-auto w-full max-w-4xl">{children}</div>
      </main>
    </div>
  );
}

const iconProps = {
  width: 18,
  height: 18,
  viewBox: "0 0 20 20",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
  focusable: false,
};

function CommunitiesIcon({ active }: { active?: boolean }) {
  return (
    <svg {...iconProps} className={active ? "text-accent" : undefined}>
      <circle cx="7.5" cy="7" r="2.75" />
      <path d="M2.75 16c.6-2.6 2.5-4 4.75-4s4.15 1.4 4.75 4" />
      <path d="M13 4.6a2.6 2.6 0 010 4.8M14.75 12.3c1.3.5 2.2 1.7 2.5 3.7" />
    </svg>
  );
}

function SettingsIcon({ active }: { active?: boolean }) {
  return (
    <svg {...iconProps} className={active ? "text-accent" : undefined}>
      <path d="M3.5 6h8M15 6h1.5M3.5 14H5M8.5 14h8" />
      <circle cx="13" cy="6" r="2" />
      <circle cx="6.75" cy="14" r="2" />
    </svg>
  );
}

function LogoutIcon() {
  return (
    <svg {...iconProps}>
      <path d="M8 3.5H5.25A1.75 1.75 0 003.5 5.25v9.5c0 .97.78 1.75 1.75 1.75H8" />
      <path d="M12.5 13.5L16 10l-3.5-3.5M16 10H8" />
    </svg>
  );
}
