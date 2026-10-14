"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { EmptyState, LoadingRow } from "@/components/ui/PageHeader";
import { apiRequest } from "@/lib/api/client";
import type { Plan } from "@/lib/api/types";
import { creatorKeys, useGroupConnection, usePlans } from "@/lib/creator";
import { errorText } from "@/lib/errors";
import { formatDays, formatRupees } from "@/lib/format";

import { PlanForm, type PlanValues } from "./PlanForm";

/** Plans for a community, shown as the passes members will buy. Creating is locked until the group is connected. */
export function PlansSection({ communityId }: { communityId: string }) {
  const queryClient = useQueryClient();
  const connection = useGroupConnection(communityId);
  const { data: plans, error, isPending } = usePlans(communityId);
  const [mode, setMode] = useState<"closed" | "new" | { edit: Plan }>("closed");
  const [confirmDeactivate, setConfirmDeactivate] = useState<Plan | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const connected = connection.data?.status === "CONNECTED";
  const refresh = () => queryClient.invalidateQueries({ queryKey: [...creatorKeys.communities, "plans", communityId] });

  const toggle = useMutation({
    mutationFn: (plan: Plan) =>
      apiRequest<Plan>(`/plans/${plan.id}/${plan.is_active ? "deactivate" : "activate"}`, { method: "PATCH" }),
    onSuccess: async () => {
      setActionError(null);
      setConfirmDeactivate(null);
      await refresh();
    },
    onError: (err) => {
      setConfirmDeactivate(null);
      setActionError(errorText(err));
    },
  });

  async function save(values: PlanValues) {
    if (typeof mode === "object") {
      await apiRequest<Plan>(`/plans/${mode.edit.id}`, { method: "PATCH", body: values });
    } else {
      await apiRequest<Plan>(`/communities/${communityId}/plans`, {
        method: "POST",
        body: {
          name: values.name,
          price: values.price,
          duration_days: values.duration_days,
          ...(values.description ? { description: values.description } : {}),
        },
      });
    }
    await refresh();
    setMode("closed");
  }

  return (
    <section aria-labelledby="plans-heading" className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h2 id="plans-heading" className="text-xl font-semibold">
            Plans
          </h2>
          <p className="text-sm text-ink-muted">What members can buy. Active plans are on sale.</p>
        </div>
        {mode === "closed" && (
          <Button onClick={() => setMode("new")} disabled={!connected}>
            New plan
          </Button>
        )}
      </div>

      {!connected && !connection.isPending && (
        <Alert tone="info" title="Connect the Telegram group to create plans.">
          Members can only buy a plan for a community whose group is connected.
        </Alert>
      )}

      {actionError && <Alert tone="danger" title={actionError} />}

      {mode !== "closed" && (
        <PlanForm
          key={typeof mode === "object" ? mode.edit.id : "new"}
          plan={typeof mode === "object" ? mode.edit : undefined}
          submitLabel={typeof mode === "object" ? "Save changes" : "Create plan"}
          onSubmit={save}
          onCancel={() => setMode("closed")}
        />
      )}

      {error ? (
        <Alert tone="danger" title="Couldn't load plans.">
          {errorText(error)}
        </Alert>
      ) : isPending ? (
        <LoadingRow label="Loading plans…" />
      ) : plans.length === 0 ? (
        mode === "closed" && (
          <EmptyState title="No plans yet">
            {connected ? "Create the first plan members can buy." : "Plans unlock once the group is connected."}
          </EmptyState>
        )
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2">
          {plans.map((plan) => (
            <li key={plan.id} aria-label={plan.name} className="flex min-w-0 flex-col gap-3">
              <PlanPass plan={plan} />
              <div className="flex flex-wrap gap-2">
                <Button variant="secondary" size="sm" aria-label={`Edit ${plan.name}`} onClick={() => setMode({ edit: plan })}>
                  Edit
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label={`${plan.is_active ? "Deactivate" : "Activate"} ${plan.name}`}
                  loading={toggle.isPending && toggle.variables?.id === plan.id}
                  onClick={() => (plan.is_active ? setConfirmDeactivate(plan) : toggle.mutate(plan))}
                >
                  {plan.is_active ? "Deactivate" : "Activate"}
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {confirmDeactivate && (
        <ConfirmDialog
          title={`Deactivate ${confirmDeactivate.name}?`}
          confirmLabel="Deactivate"
          danger
          busy={toggle.isPending}
          onConfirm={() => toggle.mutate(confirmDeactivate)}
          onCancel={() => setConfirmDeactivate(null)}
        >
          It stops being on sale. Members who already paid keep their subscription.
        </ConfirmDialog>
      )}
    </section>
  );
}

/** The access pass: marigold when on sale, outlined when not. */
export function PlanPass({ plan, footer }: { plan: Plan; footer?: React.ReactNode }) {
  const active = plan.is_active;
  return (
    <div
      className={`pass-notch flex min-h-40 flex-col justify-between gap-6 rounded-[var(--radius-pass)] p-5 ${
        active ? "bg-pass text-pass-ink" : "border border-dashed border-line-strong bg-surface-sunken text-ink"
      }`}
      style={{ ["--notch-y" as string]: "55%" }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="break-words font-display text-lg font-semibold leading-tight">{plan.name}</p>
          {plan.description && <p className={`mt-1 text-sm ${active ? "" : "text-ink-muted"}`}>{plan.description}</p>}
        </div>
        <span
          className={`inline-flex h-6 shrink-0 items-center rounded-full px-2.5 text-[13px] font-medium ${
            active ? "bg-pass-ink text-pass" : "bg-neutral-soft text-neutral"
          }`}
        >
          {active ? "On sale" : "Inactive"}
        </span>
      </div>
      <div className="flex items-end justify-between gap-3">
        <p className="font-display text-4xl font-semibold leading-none tabular">{formatRupees(plan.price)}</p>
        <p className="text-sm">{formatDays(plan.duration_days)}</p>
      </div>
      {footer}
    </div>
  );
}
