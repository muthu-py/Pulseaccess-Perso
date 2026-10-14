"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type ChangeEvent, type FormEvent } from "react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { ApiError, apiRequest } from "@/lib/api/client";
import { authErrorMessage } from "@/lib/auth-errors";

type Fields = { name: string; username: string; email: string; phone: string };
type FieldErrors = Partial<Record<keyof Fields, string>>;

export function validateSignup(v: Fields): FieldErrors {
  const errors: FieldErrors = {};
  if (!v.name.trim()) errors.name = "Enter your name.";
  if (v.username.length < 3) errors.username = "Use at least 3 characters.";
  else if (!/^[a-zA-Z0-9_]+$/.test(v.username)) errors.username = "Use only letters, numbers and underscores.";
  if (!/^\S+@\S+\.\S+$/.test(v.email.trim())) errors.email = "Enter a valid email address.";
  if (v.phone && !/^\+\d{8,15}$/.test(v.phone.replace(/[\s-]/g, ""))) {
    errors.phone = "Include the country code, e.g. +919876543210.";
  }
  return errors;
}

export function SignupForm() {
  const router = useRouter();
  const [values, setValues] = useState<Fields>({ name: "", username: "", email: "", phone: "" });
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const bind = (key: keyof Fields) => ({
    value: values[key],
    error: errors[key],
    onChange: (e: ChangeEvent<HTMLInputElement>) => setValues((prev) => ({ ...prev, [key]: e.target.value })),
  });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    const found = validateSignup(values);
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setSubmitting(true);
    try {
      const phone = values.phone.replace(/[\s-]/g, "");
      const email = values.email.trim();
      await apiRequest("/auth/register", {
        method: "POST",
        auth: null,
        body: { name: values.name.trim(), username: values.username, email, ...(phone ? { phone } : {}) },
      });
      router.push(`/login?registered=1&identifier=${encodeURIComponent(email)}`);
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fields).length > 0) {
        setErrors(err.fields as FieldErrors);
      } else {
        setFormError(authErrorMessage(err));
      }
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
      {formError && <Alert tone="danger" title={formError} />}
      <TextField label="Name" autoComplete="name" required {...bind("name")} />
      <TextField
        label="Username"
        autoComplete="username"
        hint="Letters, numbers and underscores. At least 3 characters."
        required
        {...bind("username")}
      />
      <TextField label="Email" type="email" autoComplete="email" required {...bind("email")} />
      <TextField
        label="Phone (optional)"
        type="tel"
        autoComplete="tel"
        hint="With country code. You'll need it later to connect Telegram."
        {...bind("phone")}
      />
      <Button type="submit" loading={submitting}>
        Create account
      </Button>
      <p className="text-sm text-ink-muted">
        Already have an account?{" "}
        <Link href="/login" className="text-accent underline underline-offset-4">
          Log in
        </Link>
      </p>
    </form>
  );
}
