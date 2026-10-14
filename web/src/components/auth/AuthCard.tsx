import Link from "next/link";
import type { ReactNode } from "react";

export function AuthCard({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <main id="main" className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center gap-6 px-6 py-16">
      <Link href="/" className="text-sm font-medium text-ink-muted">
        PulseAccess
      </Link>
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="text-ink-muted">{subtitle}</p>}
      </div>
      <div className="rounded-[var(--radius-card)] border border-line bg-surface p-6">{children}</div>
    </main>
  );
}
