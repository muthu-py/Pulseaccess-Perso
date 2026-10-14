"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Spinner } from "@/components/ui/Spinner";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ApiError, apiRequest } from "@/lib/api/client";
import type { Community } from "@/lib/api/types";
import { creatorKeys, useCommunity } from "@/lib/creator";
import { errorText } from "@/lib/errors";

import { CommunityForm } from "./CommunityForm";
import { ConnectionPanel } from "./ConnectionPanel";

export function CommunityDetail() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const { data: community, error, isPending } = useCommunity(id);
  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const refresh = () => queryClient.invalidateQueries({ queryKey: creatorKeys.communities });

  const toggle = useMutation({
    mutationFn: (action: "activate" | "deactivate") =>
      apiRequest<Community>(`/communities/${id}/${action}`, { method: "PATCH" }),
    onSuccess: async () => {
      setConfirming(false);
      setActionError(null);
      await refresh();
    },
    onError: (err) => {
      setConfirming(false);
      setActionError(errorText(err));
    },
  });

  if (isPending) {
    return (
      <p className="flex items-center gap-2 text-ink-muted">
        <Spinner label="Loading" /> Loading…
      </p>
    );
  }

  if (error) {
    const missing = error instanceof ApiError && error.code === "COMMUNITY_NOT_FOUND";
    return (
      <div className="flex max-w-xl flex-col gap-3">
        <Alert tone="danger" title={missing ? "Community not found." : "Couldn't load this community."}>
          {missing ? "It may have been removed, or the link is wrong." : errorText(error)}
        </Alert>
        <Link href="/app" className="text-sm text-accent underline underline-offset-4">
          Back to communities
        </Link>
      </div>
    );
  }

  const nextAction = community.is_active ? "deactivate" : "activate";

  return (
    <div className="flex max-w-xl flex-col gap-6">
      <Link href="/app" className="text-sm text-accent underline underline-offset-4">
        Back to communities
      </Link>

      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">{community.name}</h1>
          <StatusBadge kind="connection" value={community.telegram_connected ? "CONNECTED" : "NOT_CONNECTED"} />
          {!community.is_active && (
            <span className="inline-flex h-6 items-center rounded-full bg-neutral-soft px-2.5 text-[13px] font-medium text-neutral">
              Inactive
            </span>
          )}
        </div>
        {community.description && <p className="text-ink-muted">{community.description}</p>}
      </div>

      {actionError && <Alert tone="danger" title={actionError} />}

      <ConnectionPanel communityId={community.id} />

      {editing ? (
        <CommunityForm
          initial={community}
          submitLabel="Save changes"
          onCancel={() => setEditing(false)}
          onSubmit={async (values) => {
            await apiRequest<Community>(`/communities/${id}`, { method: "PATCH", body: values });
            await refresh();
            setEditing(false);
          }}
        />
      ) : (
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setEditing(true)}>
            Edit details
          </Button>
          <Button variant={community.is_active ? "secondary" : "primary"} onClick={() => setConfirming(true)}>
            {community.is_active ? "Deactivate" : "Activate"}
          </Button>
        </div>
      )}

      {confirming && (
        <ConfirmDialog
          title={community.is_active ? `Deactivate ${community.name}?` : `Activate ${community.name}?`}
          confirmLabel={community.is_active ? "Deactivate" : "Activate"}
          danger={community.is_active}
          busy={toggle.isPending}
          onConfirm={() => toggle.mutate(nextAction)}
          onCancel={() => setConfirming(false)}
        >
          {community.is_active
            ? "It moves to the Inactive tab and stops being offered to new members."
            : "It moves back to the Active tab."}
        </ConfirmDialog>
      )}
    </div>
  );
}
