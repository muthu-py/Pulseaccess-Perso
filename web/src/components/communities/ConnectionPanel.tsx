"use client";

import { Alert } from "@/components/ui/Alert";
import { Pulse } from "@/components/ui/Brand";
import { LoadingRow } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useGroupConnection } from "@/lib/creator";
import { errorText } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";

function Bot() {
  const BOT_USERNAME = process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME?.replace(/^@/, "");
  return BOT_USERNAME ? (
    <strong translate="no" className="font-medium text-ink">
      @{BOT_USERNAME}
    </strong>
  ) : (
    <>the PulseAccess bot</>
  );
}

/** The two admin rights, written as Telegram shows them. */
function Permissions() {
  return (
    <ul className="mt-2 flex flex-col divide-y divide-line overflow-hidden rounded-[10px] border border-line bg-surface text-sm text-ink">
      {["Invite users via link", "Ban users"].map((p) => (
        <li key={p} className="flex items-center justify-between gap-3 px-3.5 py-2.5">
          <span>{p}</span>
          <span aria-hidden="true" className="relative h-5 w-9 shrink-0 rounded-full bg-accent">
            <span className="absolute top-0.5 left-[18px] size-4 rounded-full bg-accent-ink" />
          </span>
        </li>
      ))}
    </ul>
  );
}

/** Telegram group connection, driven entirely by the status the backend reports. */
export function ConnectionPanel({ communityId }: { communityId: string }) {
  const { data, error, isPending } = useGroupConnection(communityId);

  return (
    <section aria-labelledby="group-heading" className="flex flex-col gap-5 rounded-[var(--radius-card)] border border-line bg-surface p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="group-heading" className="text-xl font-semibold">
          Telegram group
        </h2>
        {data && <StatusBadge kind="connection" value={data.status} />}
      </div>

      {isPending && <LoadingRow label="Checking connection…" />}

      {error && !data && (
        <Alert tone="danger" title="Couldn't check the connection.">
          {errorText(error)}
        </Alert>
      )}

      {data?.status === "CONNECTED" && (
        <dl className="grid gap-x-8 gap-y-3 text-sm sm:grid-cols-[auto_1fr]">
          <dt className="text-ink-muted">Group chat ID</dt>
          <dd translate="no" className="font-mono break-all">
            {data.telegram_chat_id ?? "Unknown"}
          </dd>
          {data.connected_at && (
            <>
              <dt className="text-ink-muted">Connected</dt>
              <dd className="tabular">{formatDateTime(data.connected_at)}</dd>
            </>
          )}
        </dl>
      )}

      {data?.status === "NEEDS_ATTENTION" && (
        <Alert tone="warning" title="PulseAccess can't manage this group right now.">
          The bot is in the group but is missing a permission, or was removed. Check that <Bot /> is still in the group
          and is an admin with:
          <Permissions />
          <span className="mt-2 block">This page updates by itself once it is fixed.</span>
        </Alert>
      )}

      {data && data.status !== "CONNECTED" && data.status !== "NEEDS_ATTENTION" && (
        <>
          <ol className="flex flex-col gap-5">
            <SetupStep n={1} title="Open your Telegram group">
              Or create one. Use the Telegram account you connected to PulseAccess.
            </SetupStep>
            <SetupStep n={2} title={<>Add <Bot /> as a member</>}>
              Search for it by username in the group&apos;s Add members screen.
            </SetupStep>
            <SetupStep n={3} title="Make it an admin with these permissions">
              <Permissions />
            </SetupStep>
          </ol>
          <div className="border-t border-line pt-4">
            <Pulse>Waiting for the bot to be added. This page updates by itself.</Pulse>
          </div>
        </>
      )}
    </section>
  );
}

function SetupStep({ n, title, children }: { n: number; title: React.ReactNode; children: React.ReactNode }) {
  return (
    <li className="grid grid-cols-[1.75rem_minmax(0,1fr)] gap-x-3">
      <span className="flex size-7 items-center justify-center rounded-full border border-line-strong text-sm font-medium tabular text-ink">
        {n}
      </span>
      <div className="flex flex-col gap-1 pt-0.5">
        <p className="font-medium text-ink">{title}</p>
        <div className="text-sm text-ink-muted">{children}</div>
      </div>
    </li>
  );
}

