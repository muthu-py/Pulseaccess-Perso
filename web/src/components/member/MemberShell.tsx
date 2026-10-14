"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

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

  return (
    <div className="flex flex-1 flex-col">
      <header className="flex h-14 items-center justify-between border-b border-line bg-surface px-6">
        <div className="flex items-center gap-6">
          <Link href="/m/subscriptions" className="font-semibold">
            PulseAccess
          </Link>
          <nav aria-label="Main" className="flex gap-4 text-[15px]">
            <Link href="/m/subscriptions" className="text-ink-muted hover:text-ink">
              My subscriptions
            </Link>
            <Link href="/m/connect-telegram" className="text-ink-muted hover:text-ink">
              Telegram
            </Link>
          </nav>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            signOut();
            router.replace("/m/login");
          }}
        >
          Log out
        </Button>
      </header>
      <main id="main" className="mx-auto w-full max-w-3xl flex-1 p-6">{children}</main>
    </div>
  );
}
