"use client";

import Link from "next/link";
import { useState } from "react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { EmptyState, LoadingRow, PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { errorText } from "@/lib/errors";
import { formatDate } from "@/lib/format";
import { fetchInviteLink, useSubscriptions } from "@/lib/member";

/** Days left until `iso`, or null if it has passed. */
function daysLeft(iso: string): number | null {
  const ms = new Date(iso).getTime() - Date.now();
  return ms > 0 ? Math.ceil(ms / 86_400_000) : null;
}

/**
 * Join Telegram group button for an active subscription.
 *
 * NOTE: The `/subscriptions/me` API returns only `plan_id`, not `community_id`.
 * `POST /telegram/communities/{community_id}/invite` requires `community_id`.
 * Until the backend adds `community_id` (or `community` object) to `SubscriptionResponse`,
 * this button cannot call the invite endpoint from this page. We show a fallback message instead.
 */
function JoinGroupButton({ communityId }: { communityId?: string }) {
  const [joining, setJoining] = useState(false);
  const [joinError, setJoinError] = useState<string | null>(null);
  const [joined, setJoined] = useState(false);

  if (!communityId) {
    // Backend gap: community_id is not in the subscription response.
    // Direct the member to Telegram DMs where the bot already sent an invite.
    return (
      <p className="text-sm text-ink-muted">
        Check your Telegram DMs — the bot sent you a join button when you paid.
      </p>
    );
  }

  async function handleJoin() {
    if (!communityId) return;
    setJoining(true);
    setJoinError(null);
    try {
      const { invite_link } = await fetchInviteLink(communityId);
      window.open(invite_link, "_blank", "noopener,noreferrer");
      setJoined(true);
    } catch (err) {
      setJoinError(errorText(err));
    } finally {
      setJoining(false);
    }
  }

  return (
    <div className="flex flex-col gap-1.5">
      {joinError && <p className="text-sm text-danger">{joinError}</p>}
      <Button
        size="sm"
        loading={joining}
        onClick={handleJoin}
        aria-label="Join the Telegram group"
      >
        {joined ? "Open again" : "Join Telegram group"}
      </Button>
    </div>
  );
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
            const communityId: string | undefined = s.community_id ?? undefined;

            return (
              <li
                key={s.id}
                className="flex flex-wrap items-start justify-between gap-4 rounded-[var(--radius-card)] border border-line bg-surface p-5"
              >
                <div className="flex min-w-0 flex-col gap-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge kind="subscription" value={s.status} />
                    {left !== null && (
                      <span className="text-sm font-medium text-ink-muted tabular">
                        {left} {left === 1 ? "day" : "days"} left
                      </span>
                    )}
                  </div>
                  <p className="font-display text-base font-semibold tabular">
                    {formatDate(s.starts_at)} → {formatDate(s.ends_at)}
                  </p>
                  <p translate="no" className="truncate font-mono text-xs text-ink-subtle">
                    {s.id}
                  </p>
                  <p className="text-xs text-ink-muted">
                    Plan ID:{" "}
                    <span translate="no" className="font-mono">
                      {s.plan_id}
                    </span>
                  </p>
                </div>

                <div className="flex flex-col items-end gap-3">
                  {s.status === "active" && (
                    <JoinGroupButton communityId={communityId} />
                  )}
                  {(s.status === "expired" || s.status === "cancelled") && (
                    // We can't deep-link directly to the community without community_id.
                    // When community_id is available from the API, replace this with:
                    // <Link href={`/c/${s.community_id}`} ...>Renew</Link>
                    <p className="text-sm text-ink-muted">
                      To renew,{" "}
                      <span className="font-medium text-ink">
                        open the community link from the creator
                      </span>{" "}
                      and choose a plan.
                    </p>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <p className="text-xs text-ink-subtle">
        Plan and community names are not yet included in the subscription API response. When they
        are, this page will show them.{" "}
        <Link href="/m/connect-telegram" className="text-accent underline underline-offset-4">
          Make sure Telegram is connected
        </Link>{" "}
        so the bot can let you in.
      </p>
    </div>
  );
}
