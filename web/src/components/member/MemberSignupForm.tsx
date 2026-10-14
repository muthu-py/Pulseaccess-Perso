"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type ChangeEvent, type FormEvent } from "react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { ApiError, apiRequest } from "@/lib/api/client";
import { authErrorMessage } from "@/lib/auth-errors";
import { safeNext } from "@/lib/safe-next";

type Fields = { name: string; email: string; phone: string };
type FieldErrors = Partial<Record<keyof Fields, string>>;

export function validateMemberSignup(v: Fields): FieldErrors {
  const errors: FieldErrors = {};
  if (!v.name.trim()) errors.name = "Enter your name.";
  if (!/^\S+@\S+\.\S+$/.test(v.email.trim())) errors.email = "Enter a valid email address.";
  if (!/^\+\d{8,15}$/.test(v.phone.replace(/[\s-]/g, ""))) {
    errors.phone = "Include the country code, e.g. +919876543210.";
  }
  return errors;
}

export function MemberSignupForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [values, setValues] = useState<Fields>({ name: "", email: "", phone: "" });
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const next = safeNext(params.get("next"), "");
  const nextQuery = next ? `&next=${encodeURIComponent(next)}` : "";

  const bind = (key: keyof Fields) => ({
    value: values[key],
    error: errors[key],
    onChange: (e: ChangeEvent<HTMLInputElement>) => setValues((prev) => ({ ...prev, [key]: e.target.value })),
  });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    const found = validateMemberSignup(values);
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setSubmitting(true);
    try {
      const email = values.email.trim();
      await apiRequest("/members/register", {
        method: "POST",
        auth: null,
        body: { name: values.name.trim(), email, phone: values.phone.replace(/[\s-]/g, "") },
      });
      setSubmitting(false);
      router.push(`/m/login?registered=1&identifier=${encodeURIComponent(email)}${nextQuery}`);
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fields).length > 0) setErrors(err.fields as FieldErrors);
      else setFormError(authErrorMessage(err));
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
      {formError && <Alert tone="danger" title={formError} />}
      <TextField label="Name" name="name" autoComplete="name" placeholder="Ravi Shah" required {...bind("name")} />
      <TextField label="Email" name="email" type="email" autoComplete="email" placeholder="you@example.com" required {...bind("email")} />
      <TextField
        label="Phone"
        name="phone"
        type="tel"
        autoComplete="tel"
        placeholder="+919876543210"
        hint="With country code. Use the number on your Telegram account: it has to match when you link Telegram."
        required
        {...bind("phone")}
      />
      <Button type="submit" size="lg" className="w-full" loading={submitting}>
        Create account
      </Button>
      <p className="text-sm text-ink-muted">
        Already have an account?{" "}
        <Link href={`/m/login${next ? `?next=${encodeURIComponent(next)}` : ""}`} className="text-accent underline underline-offset-4">
          Log in
        </Link>
      </p>
    </form>
  );
}
