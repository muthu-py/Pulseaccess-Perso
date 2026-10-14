"use client";

import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { errorText } from "@/lib/errors";
import { useSubscriptions } from "@/lib/member";

const date = (iso: string) => new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });

export function Subscriptions() {
  const { data, error, isPending } = useSubscriptions();

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">My subscriptions</h1>

      {isPending ? (
        <p className="flex items-center gap-2 text-ink-muted">
          <Spinner label="Loading" /> Loading…
        </p>
      ) : error ? (
        <Alert tone="danger" title="Couldn't load your subscriptions.">
          {errorText(error)}
        </Alert>
      ) : data.subscriptions.length === 0 ? (
        <p className="rounded-[var(--radius-card)] border border-dashed border-line-strong p-6 text-ink-muted">
          You have no subscriptions yet. Open a community link from its creator to choose a plan.
        </p>
      ) : (
        <ul className="flex flex-col divide-y divide-line rounded-[var(--radius-card)] border border-line bg-surface">
          {data.subscriptions.map((s) => (
            <li key={s.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
              <div className="flex flex-col text-sm">
                <span className="font-medium">
                  {date(s.starts_at)} to {date(s.ends_at)}
                </span>
                <span className="font-mono text-ink-subtle">{s.id}</span>
              </div>
              <StatusBadge kind="subscription" value={s.status} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
