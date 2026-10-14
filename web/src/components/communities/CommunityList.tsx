"use client";

import Link from "next/link";
import { useState } from "react";

import { Alert } from "@/components/ui/Alert";
import { buttonClass } from "@/components/ui/Button";
import { EmptyState, LoadingRow, PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { PAGE_SIZE, useCommunities } from "@/lib/creator";
import { errorText } from "@/lib/errors";
import { formatDate } from "@/lib/format";

type Tab = "active" | "inactive";

const TABS: { id: Tab; label: string }[] = [
  { id: "active", label: "Active" },
  { id: "inactive", label: "Inactive" },
];

export function CommunityList() {
  const [tab, setTab] = useState<Tab>("active");
  const [page, setPage] = useState(1);
  const { data, error, isPending, isPlaceholderData } = useCommunities(tab, page);

  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        title="Communities"
        description="Each community is one Telegram group with its own plans."
        actions={
          <Link href="/app/communities/new" className={buttonClass("primary", "md")}>
            New community
          </Link>
        }
      />

      <div
        role="tablist"
        aria-label="Community status"
        className="inline-flex w-fit gap-1 rounded-[calc(var(--radius-control)+4px)] bg-surface-sunken p-1"
      >
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
            className={`rounded-[var(--radius-control)] px-4 py-1.5 text-sm transition-[background-color,color,box-shadow] ${
              tab === t.id
                ? "bg-surface font-medium text-ink shadow-[0_1px_2px_rgb(22_24_29/0.08)]"
                : "text-ink-muted hover:text-ink"
            }`}
          >
            {t.label}
            {tab === t.id && data && <span aria-hidden="true" className="ml-1.5 tabular text-ink-subtle">{data.total}</span>}
          </button>
        ))}
      </div>

      <div role="tabpanel" aria-busy={isPlaceholderData || undefined} className="flex flex-col gap-4">
        {error ? (
          <Alert tone="danger" title="Couldn't load communities.">
            {errorText(error)}
          </Alert>
        ) : isPending ? (
          <LoadingRow />
        ) : data.communities.length === 0 ? (
          tab === "active" ? (
            <EmptyState
              title="No active communities"
              action={
                <Link href="/app/communities/new" className={buttonClass("secondary", "md")}>
                  Create a community
                </Link>
              }
            >
              Create one, or reactivate one from the Inactive tab.
            </EmptyState>
          ) : (
            <EmptyState title="No inactive communities">Communities you deactivate show up here.</EmptyState>
          )
        ) : (
          <ul className="flex flex-col divide-y divide-line overflow-hidden rounded-[var(--radius-card)] border border-line bg-surface">
            {data.communities.map((c) => (
              <li key={c.id}>
                <Link
                  href={`/app/communities/${c.id}`}
                  className="group flex items-center gap-4 px-4 py-4 transition-colors hover:bg-surface-sunken sm:px-5"
                >
                  <span
                    aria-hidden="true"
                    className="flex size-10 shrink-0 items-center justify-center rounded-[10px] bg-pass font-display text-lg font-semibold text-pass-ink"
                  >
                    {c.name.trim().charAt(0).toUpperCase()}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium">{c.name}</span>
                    <span className="block truncate text-sm text-ink-muted">
                      {c.description || `Created ${formatDate(c.created_at)}`}
                    </span>
                  </span>
                  <StatusBadge kind="connection" value={c.telegram_connected ? "CONNECTED" : "NOT_CONNECTED"} />
                  <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" className="hidden shrink-0 text-ink-subtle transition-transform group-hover:translate-x-0.5 sm:block">
                    <path d="M6 3.5L10.5 8 6 12.5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
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
              className={buttonClass("secondary", "sm")}
            >
              Previous
            </button>
            <span className="tabular">
              Page {page} of {pages}
            </span>
            <button
              type="button"
              disabled={page >= pages}
              onClick={() => setPage((p) => p + 1)}
              className={buttonClass("secondary", "sm")}
            >
              Next
            </button>
          </nav>
        )}
      </div>
    </div>
  );
}
