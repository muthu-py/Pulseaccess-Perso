"use client";

import { useState, type FormEvent } from "react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import type { Plan } from "@/lib/api/types";
import { ApiError } from "@/lib/api/client";
import { errorText } from "@/lib/errors";

export type PlanValues = { name: string; description: string | null; price: string; duration_days: number };

type Errors = Partial<Record<"name" | "description" | "price" | "duration_days", string>>;

const MIN_PRICE = 1;
const MAX_PRICE = 500000;
const MAX_DAYS = 3650;

export function validatePlan(v: { name: string; price: string; duration: string; description: string }): Errors {
  const errors: Errors = {};
  const name = v.name.trim();
  if (name.length < 2 || name.length > 100) errors.name = "Use 2 to 100 characters.";
  if (!/^\d+(\.\d{1,2})?$/.test(v.price.trim())) {
    errors.price = "Enter an amount in rupees, with at most 2 decimals.";
  } else if (Number(v.price) < MIN_PRICE || Number(v.price) > MAX_PRICE) {
    errors.price = `Price must be between ₹${MIN_PRICE} and ₹${MAX_PRICE.toLocaleString("en-IN")}.`;
  }
  if (!/^\d+$/.test(v.duration.trim()) || Number(v.duration) < 1 || Number(v.duration) > MAX_DAYS) {
    errors.duration_days = `Enter a whole number of days, from 1 to ${MAX_DAYS}.`;
  }
  if (v.description.trim().length > 500) errors.description = "Use at most 500 characters.";
  return errors;
}

export function PlanForm({
  plan,
  submitLabel,
  onSubmit,
  onCancel,
}: {
  plan?: Plan;
  submitLabel: string;
  onSubmit: (values: PlanValues) => Promise<void>;
  onCancel: () => void;
}) {
  const [name, setName] = useState(plan?.name ?? "");
  const [price, setPrice] = useState(plan?.price ?? "");
  const [duration, setDuration] = useState(String(plan?.duration_days ?? 30));
  const [description, setDescription] = useState(plan?.description ?? "");
  const [errors, setErrors] = useState<Errors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    const found = validatePlan({ name, price, duration, description });
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setBusy(true);
    try {
      await onSubmit({
        name: name.trim(),
        description: description.trim() || null,
        price: Number(price).toFixed(2),
        duration_days: Number(duration),
      });
    } catch (err) {
      if (err instanceof ApiError && err.code === "DUPLICATE_PLAN_NAME") {
        setErrors({ name: "This community already has a plan with this name." });
      } else if (err instanceof ApiError && Object.keys(err.fields).length > 0) {
        setErrors(err.fields as Errors);
      } else {
        setFormError(
          errorText(err, { COMMUNITY_NOT_CONNECTED: "Connect the Telegram group before creating plans." }),
        );
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      onSubmit={submit}
      noValidate
      aria-label={plan ? `Edit ${plan.name}` : "New plan"}
      className="flex flex-col gap-4 rounded-[var(--radius-card)] border border-line-strong bg-surface p-5"
    >
      {formError && <Alert tone="danger" title={formError} />}
      <TextField label="Plan name" value={name} error={errors.name} onChange={(e) => setName(e.target.value)} required />
      <div className="grid gap-4 sm:grid-cols-2">
        <TextField
          label="Price"
          prefix="₹"
          inputMode="decimal"
          value={price}
          error={errors.price}
          hint="Charged per period. Minimum ₹1."
          onChange={(e) => setPrice(e.target.value)}
          required
        />
        <TextField
          label="Duration (days)"
          inputMode="numeric"
          value={duration}
          error={errors.duration_days}
          hint="How long access lasts after each payment."
          onChange={(e) => setDuration(e.target.value)}
          required
        />
      </div>
      <TextField
        label="Description (optional)"
        value={description}
        error={errors.description}
        onChange={(e) => setDescription(e.target.value)}
      />
      <div className="flex gap-2">
        <Button type="submit" loading={busy}>
          {submitLabel}
        </Button>
        <Button variant="ghost" onClick={onCancel} disabled={busy}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
