"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { apiRequest } from "@/lib/api/client";
import type { Plan } from "@/lib/api/types";
import { creatorKeys, useGroupConnection, usePlans } from "@/lib/creator";
import { errorText } from "@/lib/errors";

import { PlanForm, type PlanValues } from "./PlanForm";

const days = (n: number) => `${n} ${n === 1 ? "day" : "days"}`;

/** Plans for a community. Creating is locked until the Telegram group is connected. */
export function PlansSection({ communityId }: { communityId: string }) {
  const queryClient = useQueryClient();
  const connection = useGroupConnection(communityId);
  const { data: plans, error, isPending } = usePlans(communityId);
  const [mode, setMode] = useState<"closed" | "new" | { edit: Plan }>("closed");
  const [actionError, setActionError] = useState<string | null>(null);

  const connected = connection.data?.status === "CONNECTED";
  const refresh = () => queryClient.invalidateQueries({ queryKey: [...creatorKeys.communities, "plans", communityId] });

  const toggle = useMutation({
    mutationFn: (plan: Plan) =>
      apiRequest<Plan>(`/plans/${plan.id}/${plan.is_active ? "deactivate" : "activate"}`, { method: "PATCH" }),
    onSuccess: async () => {
      setActionError(null);
      await refresh();
    },
    onError: (err) => setActionError(errorText(err)),
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
    <section aria-labelledby="plans-heading" className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <h2 id="plans-heading" className="text-lg font-semibold">
          Plans
        </h2>
        {mode === "closed" && (
          <Button size="sm" onClick={() => setMode("new")} disabled={!connected}>
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
        <p className="flex items-center gap-2 text-ink-muted">
          <Spinner label="Loading" /> Loading plans…
        </p>
      ) : plans.length === 0 ? (
        <p className="rounded-[var(--radius-card)] border border-dashed border-line-strong p-6 text-ink-muted">
          No plans yet.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-[var(--radius-card)] border border-line bg-surface">
          <table className="w-full text-left text-[15px]">
            <thead className="border-b border-line text-sm text-ink-muted">
              <tr>
                <th scope="col" className="p-3 font-medium">Name</th>
                <th scope="col" className="p-3 font-medium">Price</th>
                <th scope="col" className="p-3 font-medium">Duration</th>
                <th scope="col" className="p-3 font-medium">Status</th>
                <th scope="col" className="p-3 font-medium">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {plans.map((plan) => (
                <tr key={plan.id}>
                  <th scope="row" className="p-3 font-medium">
                    {plan.name}
                    {plan.description && <span className="block text-sm font-normal text-ink-muted">{plan.description}</span>}
                  </th>
                  <td className="p-3 whitespace-nowrap">₹{plan.price}</td>
                  <td className="p-3 whitespace-nowrap">{days(plan.duration_days)}</td>
                  <td className="p-3">
                    <StatusBadge
                      kind="subscription"
                      value={plan.is_active ? "active" : "expired"}
                      label={plan.is_active ? "Active" : "Inactive"}
                    />
                  </td>
                  <td className="p-3">
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        aria-label={`Edit ${plan.name}`}
                        onClick={() => setMode({ edit: plan })}
                      >
                        Edit
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        aria-label={`${plan.is_active ? "Deactivate" : "Activate"} ${plan.name}`}
                        loading={toggle.isPending && toggle.variables?.id === plan.id}
                        onClick={() => toggle.mutate(plan)}
                      >
                        {plan.is_active ? "Deactivate" : "Activate"}
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
