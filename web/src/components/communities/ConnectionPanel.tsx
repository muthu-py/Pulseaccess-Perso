"use client";

import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useGroupConnection } from "@/lib/creator";
import { errorText } from "@/lib/errors";

function Bot() {
  const BOT_USERNAME = process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME?.replace(/^@/, "");
  return BOT_USERNAME ? <strong className="font-medium text-ink">@{BOT_USERNAME}</strong> : <>the PulseAccess bot</>;
}

function Permissions() {
  return (
    <ul className="list-disc pl-5">
      <li>Invite users via link</li>
      <li>Ban users</li>
    </ul>
  );
}

/** Telegram group connection, driven entirely by the status the backend reports. */
export function ConnectionPanel({ communityId }: { communityId: string }) {
  const { data, error, isPending } = useGroupConnection(communityId);

  return (
    <section aria-labelledby="group-heading" className="flex flex-col gap-4 rounded-[var(--radius-card)] border border-line bg-surface p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="group-heading" className="font-medium">
          Telegram group
        </h2>
        {data && <StatusBadge kind="connection" value={data.status} />}
      </div>

      {isPending && (
        <p className="flex items-center gap-2 text-ink-muted">
          <Spinner label="Loading" /> Checking connection…
        </p>
      )}

      {error && !data && (
        <Alert tone="danger" title="Couldn't check the connection.">
          {errorText(error)}
        </Alert>
      )}

      {data?.status === "CONNECTED" && (
        <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
          <dt className="text-ink-muted">Group chat ID</dt>
          <dd className="font-mono">{data.telegram_chat_id ?? "Unknown"}</dd>
          {data.connected_at && (
            <>
              <dt className="text-ink-muted">Connected</dt>
              <dd>{new Date(data.connected_at).toLocaleString()}</dd>
            </>
          )}
        </dl>
      )}

      {data?.status === "NEEDS_ATTENTION" && (
        <>
          <Alert tone="warning" title="PulseAccess can't manage this group right now.">
            The bot is in the group but is missing a permission, or was removed. Check that <Bot /> is still in the
            group and is an admin with:
            <Permissions />
            This page updates by itself once it is fixed.
          </Alert>
        </>
      )}

      {data && data.status !== "CONNECTED" && data.status !== "NEEDS_ATTENTION" && (
        <>
          <ol className="flex list-decimal flex-col gap-2 pl-5 text-ink-muted">
            <li>Open your Telegram group, or create one.</li>
            <li>
              Add <Bot /> as a member. Do this from the Telegram account you connected.
            </li>
            <li>
              Make it an admin with these permissions:
              <Permissions />
            </li>
          </ol>
          <p role="status" className="flex items-center gap-2 text-sm text-ink-muted">
            <Spinner label="Waiting" /> Waiting for the bot to be added. This page updates by itself.
          </p>
        </>
      )}
    </section>
  );
}
