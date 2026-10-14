"use client";

import { useState, type FormEvent } from "react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { ApiError } from "@/lib/api/client";
import { errorText } from "@/lib/errors";

export type CommunityValues = { name: string; description: string | null };

const ERROR_OVERRIDES = {
  DUPLICATE_COMMUNITY_NAME: "You already have a community with this name.",
  TELEGRAM_NOT_CONNECTED: "Connect your Telegram account first.",
  PENDING_TELEGRAM_CONNECTION:
    "You already have a community waiting to be connected to a Telegram group. Finish that one first.",
};

/** Name and description form shared by "New community" and "Edit". */
export function CommunityForm({
  initial,
  submitLabel,
  onSubmit,
  onCancel,
}: {
  initial?: { name: string; description?: string | null };
  submitLabel: string;
  onSubmit: (values: CommunityValues) => Promise<void>;
  onCancel?: () => void;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [nameError, setNameError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    const trimmed = name.trim();
    if (trimmed.length < 3 || trimmed.length > 100) {
      setNameError("Use 3 to 100 characters.");
      return;
    }
    setNameError(null);
    setBusy(true);
    try {
      await onSubmit({ name: trimmed, description: description.trim() || null });
    } catch (err) {
      if (err instanceof ApiError && err.fields.name) setNameError(err.fields.name);
      else if (err instanceof ApiError && err.code === "DUPLICATE_COMMUNITY_NAME") setNameError(ERROR_OVERRIDES.DUPLICATE_COMMUNITY_NAME);
      else setFormError(errorText(err, ERROR_OVERRIDES));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate className="flex max-w-md flex-col gap-4">
      {formError && <Alert tone="danger" title={formError} />}
      <TextField
        label="Community name"
        value={name}
        error={nameError ?? undefined}
        onChange={(e) => setName(e.target.value)}
        required
      />
      <TextField
        label="Description (optional)"
        value={description}
        maxLength={500}
        onChange={(e) => setDescription(e.target.value)}
      />
      <div className="flex gap-2">
        <Button type="submit" loading={busy}>
          {submitLabel}
        </Button>
        {onCancel && (
          <Button variant="ghost" onClick={onCancel} disabled={busy}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  );
}
