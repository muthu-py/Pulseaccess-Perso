"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { usePayment } from "@/lib/member";
import { errorText } from "@/lib/errors";

/** Shows the real payment status from the backend and polls while it is still open. */
export function PaymentStatus() {
  const { id } = useParams<{ id: string }>();
  const { data: payment, error, isPending } = usePayment(id);

  if (isPending) {
    return (
      <p className="flex items-center gap-2 text-ink-muted">
        <Spinner label="Loading" /> Loading payment…
      </p>
    );
  }
  if (error || !payment) {
    return (
      <Alert tone="danger" title="Couldn't load this payment.">
        {errorText(error, { PAYMENT_NOT_FOUND: "We couldn't find this payment on your account." })}
      </Alert>
    );
  }

  const amount = `₹${(payment.amount_paise / 100).toFixed(2)}`;

  return (
    <div className="flex max-w-xl flex-col gap-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Payment</h1>
        <StatusBadge kind="payment" value={payment.status} />
      </div>

      <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
        <dt className="text-ink-muted">Amount</dt>
        <dd>{amount}</dd>
        <dt className="text-ink-muted">Payment ID</dt>
        <dd className="font-mono break-all">{payment.id}</dd>
      </dl>

      {payment.status === "created" && (
        <div className="flex flex-col gap-3">
          {payment.payment_link_url && (
            <div>
              <a
                href={payment.payment_link_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex h-10 items-center rounded-[var(--radius-control)] bg-accent px-4 text-[15px] font-medium text-accent-ink hover:bg-accent-hover"
              >
                Pay {amount} on Razorpay
              </a>
            </div>
          )}
          <p className="flex items-center gap-2 text-sm text-ink-muted">
            <Spinner label="Waiting" /> Waiting for your payment. Keep this tab open: it updates by itself.
          </p>
          {payment.expires_at && (
            <p className="text-sm text-ink-subtle">Link expires {new Date(payment.expires_at).toLocaleString()}.</p>
          )}
        </div>
      )}

      {payment.status === "paid" && (
        <Alert tone="success" title="Payment received.">
          Your subscription appears under{" "}
          <Link href="/m/subscriptions" className="text-accent underline underline-offset-4">
            My subscriptions
          </Link>
          .
        </Alert>
      )}

      {(payment.status === "expired" || payment.status === "cancelled") && (
        <Alert tone="warning" title={payment.status === "expired" ? "This payment link expired." : "This payment was cancelled."}>
          You were not charged for this link. Go back to the community page and choose the plan again to get a new link.
        </Alert>
      )}
    </div>
  );
}
