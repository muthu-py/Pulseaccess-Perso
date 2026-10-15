"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useState } from "react";

import { Alert } from "@/components/ui/Alert";
import { Pulse } from "@/components/ui/Brand";
import { Button, buttonClass } from "@/components/ui/Button";
import { LoadingRow } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { errorText } from "@/lib/errors";
import { formatDateTime, formatRupees } from "@/lib/format";
import { fetchInviteLink, usePayment } from "@/lib/member";

/** A receipt for one payment. The status comes from the backend and is polled while the link is open. */
export function PaymentStatus() {
  const { id } = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const { data: payment, error, isPending } = usePayment(id);
  const communityId = searchParams.get("communityId") || payment?.community_id || undefined;
  const [joining, setJoining] = useState(false);
  const [joinError, setJoinError] = useState<string | null>(null);

  if (isPending) return <LoadingRow label="Loading payment…" />;
  if (error || !payment) {
    return (
      <Alert tone="danger" title="Couldn't load this payment.">
        {errorText(error, { PAYMENT_NOT_FOUND: "We couldn't find this payment on your account." })}
      </Alert>
    );
  }

  const amount = formatRupees(payment.amount_paise, "paise");
  const open = payment.status === "created";

  async function joinGroup() {
    if (!communityId) return;
    setJoining(true);
    setJoinError(null);
    try {
      const { invite_link } = await fetchInviteLink(communityId);
      window.open(invite_link, "_blank", "noopener,noreferrer");
    } catch (err) {
      setJoinError(errorText(err));
    } finally {
      setJoining(false);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-lg flex-col gap-6">
      <div className="overflow-hidden rounded-[var(--radius-pass)] border border-line bg-surface shadow-[var(--shadow-raised)]">
        <div className={`flex flex-col gap-4 p-6 sm:p-7 ${payment.status === "paid" ? "bg-pass text-pass-ink" : ""}`}>
          <div className="flex items-center justify-between gap-3">
            <h1 className="text-lg font-semibold">Payment</h1>
            <StatusBadge kind="payment" value={payment.status} />
          </div>
          <p className="font-display text-5xl font-semibold leading-none tabular">{amount}</p>
        </div>

        {/* Perforation between the stub and the details */}
        <div aria-hidden="true" className="relative h-0 border-t-2 border-dashed border-line">
          <span className="absolute -top-3 -left-3 size-6 rounded-full bg-canvas" />
          <span className="absolute -top-3 -right-3 size-6 rounded-full bg-canvas" />
        </div>

        <div className="flex flex-col gap-5 p-6 sm:p-7">
          <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-6 gap-y-2.5 text-sm">
            <dt className="text-ink-muted">Payment ID</dt>
            <dd translate="no" className="font-mono break-all">
              {payment.id}
            </dd>
            {open && payment.expires_at && (
              <>
                <dt className="text-ink-muted">Link expires</dt>
                <dd className="tabular">{formatDateTime(payment.expires_at)}</dd>
              </>
            )}
          </dl>

          {open && (
            <div className="flex flex-col gap-4">
              {payment.payment_link_url && (
                <a
                  href={payment.payment_link_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={buttonClass("primary", "lg", "w-full")}
                >
                  Pay {amount} on Razorpay
                </a>
              )}
              <Pulse>Waiting for your payment. Keep this tab open: it updates by itself.</Pulse>
            </div>
          )}

          {payment.status === "paid" && (
            <div className="flex flex-col gap-4">
              <Alert tone="success" title="Payment received.">
                Your subscription is now active. Use the button below to join the Telegram group, or open{" "}
                <Link href="/m/subscriptions" className="font-medium text-accent underline underline-offset-4">
                  My subscriptions
                </Link>{" "}
                to access it later.
              </Alert>
              {joinError && <Alert tone="danger" title={joinError} />}
              {communityId ? (
                <>
                  <Button
                    id="join-telegram-group-btn"
                    size="lg"
                    className="w-full"
                    loading={joining}
                    onClick={joinGroup}
                    aria-label="Join the Telegram group"
                  >
                    Join Telegram group
                  </Button>
                  <p className="text-center text-sm text-ink-muted">
                    The bot also sent you a join button in Telegram.
                  </p>
                </>
              ) : (
                <p className="text-sm text-ink-muted">
                  The bot sent you a join button in Telegram. Check your DMs. Your subscription also appears under{" "}
                  <Link href="/m/subscriptions" className="text-accent underline underline-offset-4">
                    My subscriptions
                  </Link>
                  .
                </p>
              )}
            </div>
          )}

          {(payment.status === "expired" || payment.status === "cancelled") && (
            <Alert
              tone="warning"
              title={
                payment.status === "expired"
                  ? "This payment link expired."
                  : "This payment was cancelled."
              }
            >
              You were not charged for this link. Go back to the community page and choose the plan again to get a new
              link.
            </Alert>
          )}
        </div>
      </div>
    </div>
  );
}
