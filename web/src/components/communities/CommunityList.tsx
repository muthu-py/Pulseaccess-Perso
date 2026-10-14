"use client";

import Link from "next/link";
import { useState } from "react";

import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { PAGE_SIZE, useCommunities } from "@/lib/creator";
import { errorText } from "@/lib/errors";

type Tab = "active" | "inactive";

const TABS: { id: Tab; label: string }[] = [
  { id: "active", label: "Active" },
  { id: "inactive", label: "Inactive" },
];

const linkButton =
  "inline-flex h-10 items-center rounded-[var(--radius-control)] bg-accent px-4 text-[15px] font-medium text-accent-ink hover:bg-accent-hover";

export function CommunityList() {
  const [tab, setTab] = useState<Tab>("active");
  const [page, setPage] = useState(1);
  const { data, error, isPending, isPlaceholderData } = useCommunities(tab, page);

  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">Communities</h1>
        <Link href="/app/communities/new" className={linkButton}>
          New community
        </Link>
      </div>

      <div role="tablist" aria-label="Community status" className="flex gap-1 border-b border-line">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            type="button"
            aria-selected={tab === t.id}
            onClick={() => {
              setTab(t.id);
              setPage(1);
            }}
            className={`-mb-px border-b-2 px-3 py-2 text-[15px] ${
              tab === t.id ? "border-accent font-medium text-ink" : "border-transparent text-ink-muted hover:text-ink"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div role="tabpanel" aria-busy={isPlaceholderData || undefined} className="flex flex-col gap-4">
        {error ? (
          <Alert tone="danger" title="Couldn't load communities.">
            {errorText(error)}
          </Alert>
        ) : isPending ? (
          <p className="flex items-center gap-2 text-ink-muted">
            <Spinner label="Loading" /> Loading…
          </p>
        ) : data.communities.length === 0 ? (
          <p className="rounded-[var(--radius-card)] border border-dashed border-line-strong p-6 text-ink-muted">
            {tab === "active"
              ? "No active communities. Create one, or reactivate one from the Inactive tab."
              : "No inactive communities."}
          </p>
        ) : (
          <ul className="flex flex-col divide-y divide-line rounded-[var(--radius-card)] border border-line bg-surface">
            {data.communities.map((c) => (
              <li key={c.id}>
                <Link
                  href={`/app/communities/${c.id}`}
                  className="flex items-center justify-between gap-4 p-4 hover:bg-surface-sunken"
                >
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{c.name}</span>
                    {c.description && <span className="block truncate text-sm text-ink-muted">{c.description}</span>}
                  </span>
                  <StatusBadge kind="connection" value={c.telegram_connected ? "CONNECTED" : "NOT_CONNECTED"} />
                </Link>
              </li>
            ))}
          </ul>
        )}

        {data && pages > 1 && (
          <nav aria-label="Pagination" className="flex items-center justify-between text-sm text-ink-muted">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="rounded-[var(--radius-control)] border border-line-strong px-3 py-1.5 enabled:hover:bg-surface-sunken disabled:opacity-55"
            >
              Previous
            </button>
            <span>
              Page {page} of {pages}
            </span>
            <button
              type="button"
              disabled={page >= pages}
              onClick={() => setPage((p) => p + 1)}
              className="rounded-[var(--radius-control)] border border-line-strong px-3 py-1.5 enabled:hover:bg-surface-sunken disabled:opacity-55"
            >
              Next
            </button>
          </nav>
        )}
      </div>
    </div>
  );
}
