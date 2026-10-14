"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { Alert } from "@/components/ui/Alert";
import { Pulse } from "@/components/ui/Brand";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { apiRequest } from "@/lib/api/client";
import type { TelegramLink } from "@/lib/api/types";
import { errorText } from "@/lib/errors";
import { useMemberTelegram, useMe } from "@/lib/member";
import { safeNext } from "@/lib/safe-next";

/** Links the member's Telegram account. The phone shared in Telegram must match the one on their account. */
export function ConnectTelegram() {
  const params = useSearchParams();
  const next = safeNext(params.get("next"), "");
  const [link, setLink] = useState<TelegramLink | null>(null);
  const [error, setError] = useState<string | null>(null);

  const telegram = useMemberTelegram({ poll: link !== null });
  const me = useMe();

  const connect = useMutation({
    mutationFn: () => apiRequest<TelegramLink>("/telegram/connect/member", { method: "POST", auth: "member" }),
    onSuccess: (data) => {
      setError(null);
      setLink(data);
    },
    onError: (err) => setError(errorText(err, { TELEGRAM_ALREADY_CONNECTED: "Your Telegram is already connected." })),
  });

  const connected = telegram.data?.connected === true;

  return (
    <div className="flex max-w-xl flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Connect Telegram</h1>
        <p className="text-ink-muted">
          PulseAccess adds you to the group after you pay, so it needs to know your Telegram account.
        </p>
      </div>

      {telegram.isPending ? (
        <p className="flex items-center gap-2 text-ink-muted">
          <Spinner label="Loading" /> Loading…
        </p>
      ) : telegram.error ? (
        <Alert tone="danger" title="Couldn't check your Telegram connection.">
          {errorText(telegram.error)}
        </Alert>
      ) : connected ? (
        <div className="flex flex-col gap-4 rounded-[var(--radius-card)] border border-line bg-surface p-5">
          <div className="flex items-center gap-3">
            <StatusBadge kind="connection" value="CONNECTED" />
            {telegram.data?.telegram_username && <span className="font-mono text-sm">@{telegram.data.telegram_username}</span>}
          </div>
          {next && (
            <div>
              <Link
                href={next}
                className="inline-flex h-10 items-center rounded-[var(--radius-control)] bg-accent px-4 text-[15px] font-medium text-accent-ink hover:bg-accent-hover"
              >
                Continue
              </Link>
            </div>
          )}
        </div>
      ) : (
        <div className="flex flex-col gap-4 rounded-[var(--radius-card)] border border-line bg-surface p-5">
          <StatusBadge kind="connection" value="NOT_CONNECTED" />
          <p className="text-ink-muted">
            Open the link, press Start in Telegram, and share your phone number
            {me.data ? (
              <>
                {" "}
                (it must be <span className="font-mono">{me.data.phone}</span>, the number on this account)
              </>
            ) : null}
            .
          </p>
          {error && <Alert tone="danger" title={error} />}
          {link ? (
            <div className="flex flex-col gap-3">
              <div className="flex flex-wrap items-center gap-3">
                <a
                  href={link.telegram_link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex h-10 items-center rounded-[var(--radius-control)] bg-accent px-4 text-[15px] font-medium text-accent-ink hover:bg-accent-hover"
                >
                  Open Telegram
                </a>
                <Button variant="ghost" onClick={() => connect.mutate()} loading={connect.isPending}>
                  Get a new link
                </Button>
              </div>
              <Pulse>Waiting for Telegram to confirm. This page updates by itself.</Pulse>
            </div>
          ) : (
            <div>
              <Button onClick={() => connect.mutate()} loading={connect.isPending}>
                Connect Telegram
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
