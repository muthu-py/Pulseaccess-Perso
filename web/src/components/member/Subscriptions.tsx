"use client";

import { Alert } from "@/components/ui/Alert";
import { EmptyState, LoadingRow, PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { errorText } from "@/lib/errors";
import { formatDate } from "@/lib/format";
import { useSubscriptions } from "@/lib/member";

/** Days left until `iso`, or null if it has passed. */
function daysLeft(iso: string): number | null {
  const ms = new Date(iso).getTime() - Date.now();
  return ms > 0 ? Math.ceil(ms / 86_400_000) : null;
}

export function Subscriptions() {
  const { data, error, isPending } = useSubscriptions();

  return (
    <div className="flex flex-col gap-8">
      <PageHeader title="My subscriptions" description="Every plan you've paid for, newest first." />

      {isPending ? (
        <LoadingRow />
      ) : error ? (
        <Alert tone="danger" title="Couldn't load your subscriptions.">
          {errorText(error)}
        </Alert>
      ) : data.subscriptions.length === 0 ? (
        <EmptyState title="No subscriptions yet">
          Open a community link from its creator to choose a plan.
        </EmptyState>
      ) : (
        <ul className="flex flex-col gap-3">
          {data.subscriptions.map((s) => {
            const left = s.status === "active" ? daysLeft(s.ends_at) : null;
            return (
              <li
                key={s.id}
                className="flex flex-wrap items-center justify-between gap-4 rounded-[var(--radius-card)] border border-line bg-surface p-5"
              >
                <div className="flex min-w-0 flex-col gap-1">
                  <p className="font-display text-lg font-semibold tabular">
                    {formatDate(s.starts_at)} to {formatDate(s.ends_at)}
                  </p>
                  <p className="text-sm text-ink-muted">
                    {left !== null ? `${left} ${left === 1 ? "day" : "days"} left` : "Ended"}
                  </p>
                  <p translate="no" className="truncate font-mono text-xs text-ink-subtle">
                    {s.id}
                  </p>
                </div>
                <StatusBadge kind="subscription" value={s.status} />
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
