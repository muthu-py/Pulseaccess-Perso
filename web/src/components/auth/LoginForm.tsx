"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { apiRequest } from "@/lib/api/client";
import type { Creator, TokenResponse } from "@/lib/api/types";
import { useAuth } from "@/lib/auth";
import { authErrorMessage } from "@/lib/auth-errors";
import { RESEND_SECONDS } from "./OtpStep";

type Step = "identifier" | "code" | "returning";

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const { state, signIn, signOut } = useAuth();

  // When redirected from signup with `sent=1`, open on the code step immediately.
  const initialIdentifier = params.get("identifier") ?? "";
  const startOnCode = params.get("sent") === "1" && !!initialIdentifier;

  const [identifier, setIdentifier] = useState(initialIdentifier);
  const [step, setStep] = useState<Step>(startOnCode ? "code" : "identifier");
  const [code, setCode] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [resendCountdown, setResendCountdown] = useState(startOnCode ? RESEND_SECONDS : 0);
  const [newCodeSent, setNewCodeSent] = useState(false);

  // "Returning user" state: loaded from GET /auth/me when a refresh cookie exists.
  const [returningName, setReturningName] = useState<string | null>(null);

  // When the auth state loads and the user is already authenticated, show the
  // "continuing as" view instead of redirecting (per the test: never skip the code step).
  useEffect(() => {
    if (state === "authenticated") {
      // Fetch the name to display
      apiRequest<Creator>("/auth/me")
        .then((creator) => {
          setReturningName(creator.name);
          setStep("returning");
        })
        .catch(() => {
          // If /auth/me fails, fall through to anonymous login
          setStep("identifier");
        });
    }
  }, [state]);


  // Countdown timer for resend button.
  useEffect(() => {
    if (resendCountdown <= 0) return;
    const id = setTimeout(() => setResendCountdown((c) => c - 1), 1000);
    return () => clearTimeout(id);
  }, [resendCountdown]);

  // Auto-submit when exactly 6 digits are entered.
  useEffect(() => {
    if (step === "code" && /^\d{6}$/.test(code) && !submitting) {
      void verifyCode();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code]);

  async function requestCode() {
    await apiRequest("/auth/request-otp", {
      method: "POST",
      auth: null,
      body: { identifier: identifier.trim() },
    });
    setStep("code");
    setCode("");
    setResendCountdown(RESEND_SECONDS);
    setNewCodeSent(false);
  }

  async function onIdentifier(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!identifier.trim()) {
      setFieldError("Enter your email or username.");
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

  async function verifyCode() {
    setFormError(null);
    if (!/^\d{6}$/.test(code)) {
      setFieldError("Enter the 6-digit code.");
      return;
    }
    setFieldError(null);
    setSubmitting(true);
    try {
      const result = await apiRequest<TokenResponse>("/auth/verify-otp", {
        method: "POST",
        auth: null,
        body: { identifier: identifier.trim(), otp_code: code },
      });
      signIn(result.access_token);
      setCode("");
      setSubmitting(false);
      const next = params.get("next");
      router.replace(next && next.startsWith("/") ? next : "/app");
    } catch (err) {
      setFormError(authErrorMessage(err));
      setSubmitting(false);
    }
  }

  async function onCode(e: FormEvent) {
    e.preventDefault();
    await verifyCode();
  }

  async function resend() {
    setFormError(null);
    setNewCodeSent(false);
    setSubmitting(true);
    try {
      await requestCode();
      setNewCodeSent(true);
    } catch (err) {
      setFormError(authErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSignOutAndSwitch() {
    await signOut();
    setReturningName(null);
    setStep("identifier");
    setCode("");
    setFormError(null);
    setFieldError(null);
  }

  // ── Step: returning user ────────────────────────────────────────────────────
  if (step === "returning" && returningName) {
    return (
      <div className="flex flex-col gap-4">
        <p className="text-ink-muted">
          This browser is already logged in. Signed in as <strong className="text-ink">{returningName}</strong>.
        </p>
        <Link
          href="/app"
          className="inline-flex h-12 w-full items-center justify-center rounded-[var(--radius-control)] bg-accent px-5 text-base font-medium text-accent-ink transition-colors hover:bg-accent-hover"
        >
          Continue to dashboard
        </Link>
        <Button
          variant="ghost"
          size="sm"
          className="w-full"
          onClick={handleSignOutAndSwitch}
        >
          Log out and use another account
        </Button>
      </div>
    );
  }

  // ── Step: enter identifier ──────────────────────────────────────────────────
  if (step === "identifier") {
    return (
      <form onSubmit={onIdentifier} noValidate className="flex flex-col gap-4">
        {params.get("registered") && !startOnCode && (
          <Alert tone="success" title="Account created. Log in with a code sent to your email." />
        )}
        {formError && <Alert tone="danger" title={formError} />}
        <TextField
          label="Email or username"
          name="identifier"
          autoComplete="username"
          spellCheck={false}
          placeholder="you@example.com or asha_trades"
          value={identifier}
          error={fieldError ?? undefined}
          onChange={(e) => setIdentifier(e.target.value)}
          required
        />
        <Button type="submit" size="lg" className="w-full" loading={submitting}>
          Send code
        </Button>
        <p className="text-sm text-ink-muted">
          New here?{" "}
          <Link href="/signup" className="text-accent underline underline-offset-4">
            Create an account
          </Link>
        </p>
      </form>
    );
  }

  // ── Step: enter OTP code ────────────────────────────────────────────────────
  const isRegistered = params.get("registered") === "1";

  return (
    <form onSubmit={onCode} noValidate className="flex flex-col gap-4">
      {/* Status message — role="status" so screen readers announce it without interrupting */}
      <div role="status" className="rounded-[var(--radius-control)] border border-line bg-surface-sunken px-4 py-3 text-sm text-ink-muted">
        {isRegistered ? (
          <div>
            <strong className="block font-medium text-ink">Account created</strong>
            <span>We sent a 6-digit code to {identifier.trim()}.</span>
          </div>
        ) : (
          `If an account matches ${identifier.trim()}, we've sent it a 6-digit code.`
        )}
      </div>
      {newCodeSent && (
        <p role="status" className="text-sm font-medium text-success">
          New code sent.
        </p>
      )}
      {formError && <Alert tone="danger" title={formError} />}
      <TextField
        autoFocus
        label="6-digit code"
        inputMode="numeric"
        autoComplete="one-time-code"
        name="otp"
        spellCheck={false}
        placeholder="123456"
        maxLength={6}
        value={code}
        error={fieldError ?? undefined}
        onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
        hint="Codes expire after 5 minutes."
        required
      />
      <Button type="submit" size="lg" className="w-full" loading={submitting}>
        Log in
      </Button>
      <div className="flex gap-2">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={resend}
          disabled={submitting || resendCountdown > 0}
          aria-live="polite"
        >
          {resendCountdown > 0 ? `Send a new code in ${resendCountdown}s` : "Send a new code"}
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => {
            setStep("identifier");
            setFormError(null);
            setFieldError(null);
          }}
        >
          Use a different account
        </Button>
      </div>
    </form>
  );
}
