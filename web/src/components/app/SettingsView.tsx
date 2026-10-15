"use client";

import Link from "next/link";
import { useState } from "react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { LoadingRow, PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useAuth } from "@/lib/auth";
import { useCreatorMe, useCreatorTelegram } from "@/lib/creator";
import { errorText } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";

function ProfileSection() {
  const { data, error, isPending } = useCreatorMe();

  if (isPending) return <LoadingRow label="Loading profile…" />;
  if (error || !data) {
    return (
      <Alert tone="danger" title="Couldn't load your profile.">
        {errorText(error)}
      </Alert>
    );
  }

  return (
    <section aria-labelledby="profile-heading" className="flex flex-col gap-4 rounded-[var(--radius-card)] border border-line bg-surface p-5 sm:p-6">
      <h2 id="profile-heading" className="text-lg font-semibold">Profile</h2>
      <dl className="grid gap-x-8 gap-y-3 text-sm sm:grid-cols-[10rem_minmax(0,1fr)]">
        <dt className="text-ink-muted">Name</dt>
        <dd className="font-medium text-ink">{data.name}</dd>

        <dt className="text-ink-muted">Username</dt>
        <dd translate="no" className="font-mono text-ink">
          {data.username}
        </dd>

        <dt className="text-ink-muted">Email</dt>
        <dd translate="no" className="text-ink">
          {data.email}
        </dd>

        {data.phone != null && (
          <>
            <dt className="text-ink-muted">Phone</dt>
            <dd translate="no" className="font-mono text-ink">
              {data.phone}
            </dd>
          </>
        )}

        <dt className="text-ink-muted">Account ID</dt>
        <dd translate="no" className="break-all font-mono text-xs text-ink-subtle">
          {data.id}
        </dd>
      </dl>

      {data.phone == null && (
        <Alert tone="info" title="No phone number set.">
          A phone number is required to connect Telegram.{" "}
          <Link href="/app/onboarding" className="font-medium text-accent underline underline-offset-4">
            Go to onboarding
          </Link>{" "}
          to add one.
        </Alert>
      )}
    </section>
  );
}

function TelegramSection() {
  const { data, error, isPending } = useCreatorTelegram();

  if (isPending) return <LoadingRow label="Checking Telegram…" />;

  return (
    <section aria-labelledby="telegram-heading" className="flex flex-col gap-4 rounded-[var(--radius-card)] border border-line bg-surface p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="telegram-heading" className="text-lg font-semibold">Telegram account</h2>
        {data && <StatusBadge kind="connection" value={data.connected ? "CONNECTED" : "NOT_CONNECTED"} />}
      </div>

      {error && (
        <Alert tone="danger" title="Couldn't check Telegram status.">
          {errorText(error)}
        </Alert>
      )}

      {data?.connected ? (
        <dl className="grid gap-x-8 gap-y-3 text-sm sm:grid-cols-[10rem_minmax(0,1fr)]">
          {data.telegram_username && (
            <>
              <dt className="text-ink-muted">Telegram username</dt>
              <dd translate="no" className="font-mono text-ink">
                @{data.telegram_username}
              </dd>
            </>
          )}
          {data.linked_at && (
            <>
              <dt className="text-ink-muted">Linked</dt>
              <dd className="tabular text-ink">{formatDateTime(data.linked_at)}</dd>
            </>
          )}
        </dl>
      ) : (
        <div className="flex flex-col gap-3">
          <p className="text-sm text-ink-muted">
            Link your Telegram account so PulseAccess can connect your communities&apos; groups.
          </p>
          <Link
            href="/app/onboarding"
            className="w-fit text-sm font-medium text-accent underline underline-offset-4 hover:text-accent-hover"
          >
            Connect Telegram in onboarding
          </Link>
        </div>
      )}
    </section>
  );
}

function SignOutSection() {
  const { signOut } = useAuth();
  const [busy, setBusy] = useState(false);

  async function handleSignOut() {
    setBusy(true);
    try {
      await signOut();
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="signout-heading" className="flex flex-col gap-4 rounded-[var(--radius-card)] border border-danger-soft bg-danger-soft p-5 sm:p-6">
      <h2 id="signout-heading" className="text-sm font-semibold text-danger">Sign out</h2>
      <p className="text-sm text-ink-muted">
        You will be returned to the login page. Your communities and plans are not affected.
      </p>
      <Button
        variant="danger"
        size="sm"
        className="w-fit"
        loading={busy}
        onClick={handleSignOut}
        id="sign-out-btn"
      >
        Sign out
      </Button>
    </section>
  );
}

export function SettingsView() {
  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        title="Settings"
        description="Your creator account and connected services."
      />
      <ProfileSection />
      <TelegramSection />
      <SignOutSection />
    </div>
  );
}
