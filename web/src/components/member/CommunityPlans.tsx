"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { Alert } from "@/components/ui/Alert";
import { PlanPass } from "@/components/plans/PlansSection";
import { EmptyState, LoadingRow, PageHeader } from "@/components/ui/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { ApiError, apiRequest } from "@/lib/api/client";
import type { Payment } from "@/lib/api/types";
import { errorText } from "@/lib/errors";
import { formatRupees } from "@/lib/format";
import { useAvailablePlans, useMemberTelegram } from "@/lib/member";

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
    <div className="flex flex-col gap-8">
      <PageHeader title="Choose a plan" description="Pay once for the days shown. Payment happens on Razorpay." />

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
        <LoadingRow label="Loading plans…" />
      ) : plans.error ? (
        <Alert tone="danger" title="Couldn't load plans.">
          {errorText(plans.error, {
            COMMUNITY_NOT_FOUND: "This community doesn't exist or isn't open for new members.",
            COMMUNITY_NOT_CONNECTED: "This community isn't open for new members yet.",
          })}
        </Alert>
      ) : plans.data.length === 0 ? (
        <EmptyState title="No plans are available right now">Check back later, or ask the community&apos;s creator.</EmptyState>
      ) : (
        <ul className="grid gap-5 sm:grid-cols-2">
          {plans.data.map((plan) => (
            <li key={plan.id} className="min-w-0">
              <PlanPass
                plan={plan}
                footer={
                  <button
                    type="button"
                    aria-label={`Pay for ${plan.name}`}
                    aria-busy={payingId === plan.id || undefined}
                    disabled={pay.isPending}
                    onClick={() => {
                      setPayingId(plan.id);
                      setError(null);
                      pay.mutate(plan.id);
                    }}
                    className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-[var(--radius-control)] bg-pass-ink text-[15px] font-medium text-pass transition-[opacity,transform] hover:opacity-90 active:translate-y-px disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {payingId === plan.id && <Spinner label="Working" />}
                    Pay {formatRupees(plan.price)}
                  </button>
                }
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
