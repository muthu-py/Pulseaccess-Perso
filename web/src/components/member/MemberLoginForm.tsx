"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { MEMBER_TOKEN_KEY, apiRequest, session } from "@/lib/api/client";
import type { Member, TokenResponse } from "@/lib/api/types";
import { authErrorMessage } from "@/lib/auth-errors";
import { useMemberAuth } from "@/lib/member-auth";
import { safeNext } from "@/lib/safe-next";

/** How many seconds to lock the Resend button. */
const RESEND_SECONDS = 30;

/** True if the member token in localStorage is still valid (not expired). */
function hasValidSavedToken(): boolean {
  try {
    const raw = localStorage.getItem(MEMBER_TOKEN_KEY);
    if (!raw) return false;
    return session.get("member") !== null;
  } catch {
    return false;
  }
}

export function MemberLoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const { signIn, signOut } = useMemberAuth();

  const next = safeNext(params.get("next"), "");
  const identifierParam = params.get("identifier") ?? "";
  const sentParam = params.get("sent") === "1";
  const registeredParam = params.get("registered") === "1";

  // ── Returning-user view ────────────────────────────────────────────────────
  // When the member already has a valid saved token, show their name and a
  // "Continue" link so they don't have to log in again.
  const [returningUser, setReturningUser] = useState<Member | null>(null);
  const [returningChecked, setReturningChecked] = useState(() => {
    if (typeof window === "undefined") return false;
    return !hasValidSavedToken();
  });

  useEffect(() => {
    if (!hasValidSavedToken()) return;
    // Fetch the profile to show their name
    apiRequest<Member>("/members/me", { auth: "member" })
      .then((me) => {
        setReturningUser(me);
        setReturningChecked(true);
      })
      .catch(() => {
        // Token bad or network error – treat as signed out
        session.clear("member");
        setReturningChecked(true);
      });
  }, []);

  // ── Form state ─────────────────────────────────────────────────────────────
  const [email, setEmail] = useState(identifierParam);
  const [step, setStep] = useState<"email" | "code">(sentParam ? "code" : "email");
  const [code, setCode] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Resend countdown
  const [resendSecondsLeft, setResendSecondsLeft] = useState(sentParam ? RESEND_SECONDS : 0);
  useEffect(() => {
    if (resendSecondsLeft <= 0) return;
    const id = window.setInterval(() => {
      setResendSecondsLeft((s) => Math.max(0, s - 1));
    }, 1000);
    return () => clearInterval(id);
  }, [resendSecondsLeft]);

  // ── Helpers ────────────────────────────────────────────────────────────────
  async function requestCode() {
    await apiRequest("/members/request-otp", {
      method: "POST",
      auth: null,
      body: { email: email.trim() },
    });
    setStep("code");
    setCode("");
    setResendSecondsLeft(RESEND_SECONDS);
  }

  const submitCode = useCallback(
    async (otp: string) => {
      setFormError(null);
      setFieldError(null);
      setSubmitting(true);
      try {
        const result = await apiRequest<TokenResponse>("/members/verify-otp", {
          method: "POST",
          auth: null,
          body: { email: email.trim() || identifierParam.trim(), otp_code: otp },
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
    },
    [email, identifierParam, signIn, router, next],
  );

  // ── Auto-submit when 6 digits are entered ──────────────────────────────────
  useEffect(() => {
    if (step === "code" && /^\d{6}$/.test(code) && !submitting) {
      const timer = setTimeout(() => {
        void submitCode(code);
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [code, step, submitting, submitCode]);

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
    await submitCode(code);
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

  function logoutAndSwitch() {
    signOut();
    localStorage.removeItem(MEMBER_TOKEN_KEY);
    setReturningUser(null);
  }

  // ── Returning-user view ────────────────────────────────────────────────────
  if (!returningChecked) {
    // Don't flash the email form while we check localStorage
    return null;
  }

  if (returningUser) {
    const continueTo = safeNext(next, "/m/subscriptions");
    return (
      <div className="flex flex-col gap-4">
        <p className="text-sm text-ink-muted">
          Signed in as <strong className="font-medium text-ink">{returningUser.name}</strong>
          {returningUser.email && (
            <> ({returningUser.email})</>
          )}
        </p>
        <Link
          href={continueTo}
          className="inline-flex h-12 w-full items-center justify-center rounded-[var(--radius-control)] bg-accent px-5 text-base font-medium text-accent-ink transition-colors hover:bg-accent-hover"
        >
          Continue
        </Link>
        <Button
          variant="ghost"
          size="sm"
          onClick={logoutAndSwitch}
        >
          Log out and use another account
        </Button>
      </div>
    );
  }

  // ── Code step ─────────────────────────────────────────────────────────────
  if (step === "code") {
    const sentEmail = email.trim() || identifierParam.trim();
    return (
      <form onSubmit={onCode} noValidate className="flex flex-col gap-4">
        {registeredParam ? (
          <Alert
            tone="success"
            title={`Account created. Log in with a code sent to ${sentEmail || "your email"}.`}
          />
        ) : (
          <Alert tone="info" title="If an account exists, a code has been sent." />
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
            variant="ghost"
            size="sm"
            type="button"
            onClick={resend}
            disabled={submitting || resendSecondsLeft > 0}
          >
            {resendSecondsLeft > 0 ? `Resend in ${resendSecondsLeft}s` : "Send a new code"}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            type="button"
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

  // ── Email step ─────────────────────────────────────────────────────────────
  return (
    <form onSubmit={onEmail} noValidate className="flex flex-col gap-4">
      {registeredParam && (
        <Alert
          tone="success"
          title={`Account created. Log in with a code sent to ${identifierParam || "your email"}.`}
        />
      )}
      {formError && <Alert tone="danger" title={formError} />}
      <TextField
        label="Email"
        name="email"
        type="email"
        autoComplete="email"
        placeholder="you@example.com"
        value={email}
        error={fieldError ?? undefined}
        onChange={(e) => setEmail(e.target.value)}
        required
      />
      <Button type="submit" size="lg" className="w-full" loading={submitting}>
        Send code
      </Button>
      <p className="text-sm text-ink-muted">
        New here?{" "}
        <Link
          href={`/m/signup${next ? `?next=${encodeURIComponent(next)}` : ""}`}
          className="text-accent underline underline-offset-4"
        >
          Create an account
        </Link>
      </p>
    </form>
  );
}
