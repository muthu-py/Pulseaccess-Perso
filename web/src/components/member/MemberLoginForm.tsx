"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { apiRequest } from "@/lib/api/client";
import type { TokenResponse } from "@/lib/api/types";
import { authErrorMessage } from "@/lib/auth-errors";
import { useMemberAuth } from "@/lib/member-auth";
import { safeNext } from "@/lib/safe-next";

export function MemberLoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const { signIn } = useMemberAuth();

  const next = safeNext(params.get("next"), "");
  const [email, setEmail] = useState(params.get("identifier") ?? "");
  const [step, setStep] = useState<"email" | "code">("email");
  const [code, setCode] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function requestCode() {
    await apiRequest("/members/request-otp", { method: "POST", auth: null, body: { email: email.trim() } });
    setStep("code");
    setCode("");
  }

  async function onEmail(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) {
      setFieldError("Enter a valid email address.");
      return;
    }
    setFieldError(null);
    setSubmitting(true);
    try {
      await requestCode();
    } catch (err) {
      setFormError(authErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function onCode(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!/^\d{6}$/.test(code)) {
      setFieldError("Enter the 6-digit code.");
      return;
    }
    setFieldError(null);
    setSubmitting(true);
    try {
      const result = await apiRequest<TokenResponse>("/members/verify-otp", {
        method: "POST",
        auth: null,
        body: { email: email.trim(), otp_code: code },
      });
      signIn(result.access_token);
      setStep("email");
      setCode("");
      setSubmitting(false);
      router.replace(safeNext(next, "/m/subscriptions"));
    } catch (err) {
      setFormError(authErrorMessage(err));
      setSubmitting(false);
    }
  }

  async function resend() {
    setFormError(null);
    setSubmitting(true);
    try {
      await requestCode();
    } catch (err) {
      setFormError(authErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  if (step === "email") {
    return (
      <form onSubmit={onEmail} noValidate className="flex flex-col gap-4">
        {params.get("registered") && (
          <Alert tone="success" title="Account created. Log in with a code sent to your email." />
        )}
        {formError && <Alert tone="danger" title={formError} />}
        <TextField
          label="Email"
          type="email"
          autoComplete="email"
          value={email}
          error={fieldError ?? undefined}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <Button type="submit" loading={submitting}>
          Send code
        </Button>
        <p className="text-sm text-ink-muted">
          New here?{" "}
          <Link href={`/m/signup${next ? `?next=${encodeURIComponent(next)}` : ""}`} className="text-accent underline underline-offset-4">
            Create an account
          </Link>
        </p>
      </form>
    );
  }

  return (
    <form onSubmit={onCode} noValidate className="flex flex-col gap-4">
      <Alert tone="info" title="If an account exists, a code has been sent." />
      {formError && <Alert tone="danger" title={formError} />}
      <TextField
        label="6-digit code"
        inputMode="numeric"
        autoComplete="one-time-code"
        maxLength={6}
        value={code}
        error={fieldError ?? undefined}
        onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
        hint="Codes expire after 5 minutes."
        required
      />
      <Button type="submit" loading={submitting}>
        Log in
      </Button>
      <div className="flex gap-2">
        <Button variant="ghost" size="sm" onClick={resend} disabled={submitting}>
          Send a new code
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            setStep("email");
            setFormError(null);
            setFieldError(null);
          }}
        >
          Use a different email
        </Button>
      </div>
    </form>
  );
}
