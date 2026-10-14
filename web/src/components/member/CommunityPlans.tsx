"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { ApiError, apiRequest } from "@/lib/api/client";
import type { Payment } from "@/lib/api/types";
import { errorText } from "@/lib/errors";
import { useAvailablePlans, useMemberTelegram } from "@/lib/member";

const days = (n: number) => `${n} ${n === 1 ? "day" : "days"}`;

/** What a member sees at /c/[communityId]: the plans they can buy. Needs a member login for now. */
export function CommunityPlans() {
  const { communityId } = useParams<{ communityId: string }>();
  const router = useRouter();
  const plans = useAvailablePlans(communityId);
  const telegram = useMemberTelegram();
  const [payingId, setPayingId] = useState<string | null>(null);
  const [needsTelegram, setNeedsTelegram] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pay = useMutation({
    mutationFn: (planId: string) =>
      apiRequest<Payment>(`/plans/${planId}/payment-link`, { method: "POST", auth: "member" }),
    onSuccess: (payment) => router.push(`/m/payments/${payment.id}`),
    onError: (err) => {
      setPayingId(null);
      if (err instanceof ApiError && err.code === "TELEGRAM_NOT_CONNECTED") {
        setNeedsTelegram(true);
        setError(null);
      } else {
        setError(
          errorText(err, {
            PLAN_UNAVAILABLE: "This plan isn't available any more. Refresh to see the current plans.",
            PLAN_NOT_FOUND: "This plan isn't available any more. Refresh to see the current plans.",
            HTTP_502: "The payment provider didn't respond. Try again in a moment.",
          }),
        );
      }
    },
  });

  const telegramMissing = needsTelegram || telegram.data?.connected === false;
  const connectHref = `/m/connect-telegram?next=${encodeURIComponent(`/c/${communityId}`)}`;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">Choose a plan</h1>

      {telegramMissing && (
        <Alert tone="warning" title="Connect Telegram before you pay.">
          We add you to the group on Telegram after payment.{" "}
          <Link href={connectHref} className="text-accent underline underline-offset-4">
            Connect Telegram
          </Link>
        </Alert>
      )}
      {error && <Alert tone="danger" title={error} />}

      {plans.isPending ? (
        <p className="flex items-center gap-2 text-ink-muted">
          <Spinner label="Loading" /> Loading plans…
        </p>
      ) : plans.error ? (
        <Alert tone="danger" title="Couldn't load plans.">
          {errorText(plans.error, {
            COMMUNITY_NOT_FOUND: "This community doesn't exist or isn't open for new members.",
            COMMUNITY_NOT_CONNECTED: "This community isn't open for new members yet.",
          })}
        </Alert>
      ) : plans.data.length === 0 ? (
        <p className="rounded-[var(--radius-card)] border border-dashed border-line-strong p-6 text-ink-muted">
          No plans are available right now.
        </p>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2">
          {plans.data.map((plan) => (
            <li key={plan.id} className="flex flex-col gap-3 rounded-[var(--radius-card)] border border-line bg-surface p-5">
              <h2 className="font-medium">{plan.name}</h2>
              <p className="text-2xl font-semibold">
                ₹{plan.price} <span className="text-base font-normal text-ink-muted">for {days(plan.duration_days)}</span>
              </p>
              {plan.description && <p className="text-sm text-ink-muted">{plan.description}</p>}
              <div className="mt-auto">
                <Button
                  aria-label={`Pay for ${plan.name}`}
                  loading={payingId === plan.id}
                  disabled={pay.isPending && payingId !== plan.id}
                  onClick={() => {
                    setPayingId(plan.id);
                    setError(null);
                    pay.mutate(plan.id);
                  }}
                >
                  Pay ₹{plan.price}
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
