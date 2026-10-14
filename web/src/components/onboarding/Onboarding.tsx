"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/icons";
import { Spinner } from "@/components/ui/Spinner";
import { TextField } from "@/components/ui/TextField";
import { ApiError, apiRequest } from "@/lib/api/client";
import type { Community, TelegramLink } from "@/lib/api/types";
import { creatorKeys, useCommunityCount, useCreatorTelegram } from "@/lib/creator";

const PHONE_PATTERN = /^\+\d{8,15}$/;

function errorText(err: unknown, overrides: Record<string, string> = {}): string {
  if (err instanceof ApiError) {
    return overrides[err.code] ?? (err.status >= 500 ? "Something went wrong on our side. Try again." : err.message);
  }
  return "Something went wrong. Try again.";
}

function Step({
  number,
  title,
  done,
  active,
  children,
}: {
  number: number;
  title: string;
  done: boolean;
  active: boolean;
  children?: ReactNode;
}) {
  return (
    <li
      aria-current={active ? "step" : undefined}
      className={`flex gap-4 rounded-[var(--radius-card)] border p-5 ${active ? "border-line-strong bg-surface" : "border-line bg-surface-sunken"}`}
    >
      <span
        className={`flex size-7 shrink-0 items-center justify-center rounded-full text-sm font-medium ${
          done ? "bg-success-soft text-success" : active ? "bg-accent text-accent-ink" : "bg-neutral-soft text-neutral"
        }`}
      >
        {done ? <Icon name="check" /> : number}
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-3">
        <h2 className="font-medium">
          {title}
          {done && <span className="sr-only"> (done)</span>}
        </h2>
        {active && children}
      </div>
    </li>
  );
}

function PhoneForm({ onSaved }: { onSaved: () => void }) {
  const [phone, setPhone] = useState("");
  const [error, setError] = useState<string | null>(null);
  const save = useMutation({
    mutationFn: (value: string) => apiRequest("/auth/phone", { method: "PUT", body: { phone: value } }),
    onSuccess: onSaved,
    onError: (err) => {
      setError(
        err instanceof ApiError && err.fields.phone
          ? err.fields.phone
          : errorText(err, { CREATOR_ALREADY_EXISTS: "That phone number is used by another account." }),
      );
    },
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const value = phone.replace(/[\s-]/g, "");
    if (!PHONE_PATTERN.test(value)) {
      setError("Include the country code, e.g. +919876543210.");
      return;
    }
    setError(null);
    save.mutate(value);
  }

  return (
    <form onSubmit={onSubmit} noValidate className="flex max-w-sm flex-col gap-3">
      <TextField
        label="Phone number"
        type="tel"
        autoComplete="tel"
        value={phone}
        error={error ?? undefined}
        onChange={(e) => setPhone(e.target.value)}
        hint="Use the number on your Telegram account, with country code."
        required
      />
      <div>
        <Button type="submit" loading={save.isPending}>
          Save phone number
        </Button>
      </div>
    </form>
  );
}

function TelegramStep({ needsPhone, onNeedsPhone }: { needsPhone: boolean; onNeedsPhone: (v: boolean) => void }) {
  const queryClient = useQueryClient();
  const [link, setLink] = useState<TelegramLink | null>(null);
  const [error, setError] = useState<string | null>(null);

  const connect = useMutation({
    mutationFn: () => apiRequest<TelegramLink>("/telegram/connect/creator", { method: "POST" }),
    onSuccess: (data) => {
      setError(null);
      onNeedsPhone(false);
      setLink(data);
    },
    onError: (err) => {
      if (err instanceof ApiError && err.code === "PHONE_REQUIRED") {
        onNeedsPhone(true);
        setError(null);
      } else if (err instanceof ApiError && err.code === "TELEGRAM_ALREADY_CONNECTED") {
        queryClient.invalidateQueries({ queryKey: creatorKeys.telegram });
      } else {
        setError(errorText(err));
      }
    },
  });

  if (needsPhone) {
    return (
      <>
        <p className="text-ink-muted">Add your phone number first. Telegram matches it to your account.</p>
        <PhoneForm onSaved={() => connect.mutate()} />
      </>
    );
  }

  return (
    <>
      <p className="text-ink-muted">
        PulseAccess needs to know which Telegram account is yours. Open the link, press Start in Telegram, and share
        your phone number when asked.
      </p>
      {error && <Alert tone="danger" title={error} />}
      {link ? (
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <a
              href={link.telegram_link}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex h-10 items-center rounded-[var(--radius-control)] bg-accent px-4 text-[15px] font-medium text-accent-ink hover:bg-accent-hover"
            >
              Open Telegram
            </a>
            <Button variant="ghost" onClick={() => connect.mutate()} loading={connect.isPending}>
              Get a new link
            </Button>
          </div>
          <p role="status" className="flex items-center gap-2 text-sm text-ink-muted">
            <Spinner label="Waiting" /> Waiting for Telegram to confirm. This page updates by itself.
          </p>
          <p className="text-sm text-ink-subtle">Link expires {new Date(link.expires_at).toLocaleTimeString()}.</p>
        </div>
      ) : (
        <div>
          <Button onClick={() => connect.mutate()} loading={connect.isPending}>
            Connect Telegram
          </Button>
        </div>
      )}
    </>
  );
}

function CommunityStep() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [nameError, setNameError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: (body: { name: string; description?: string }) =>
      apiRequest<Community>("/communities", { method: "POST", body }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: creatorKeys.communities });
      router.replace("/app");
    },
    onError: (err) => {
      if (err instanceof ApiError && err.fields.name) {
        setNameError(err.fields.name);
      } else {
        setFormError(
          errorText(err, {
            TELEGRAM_NOT_CONNECTED: "Connect your Telegram account first.",
            PENDING_TELEGRAM_CONNECTION:
              "You already have a community waiting to be connected to a Telegram group. Finish that one first.",
          }),
        );
      }
    },
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    const trimmed = name.trim();
    if (trimmed.length < 3 || trimmed.length > 100) {
      setNameError("Use 3 to 100 characters.");
      return;
    }
    setNameError(null);
    create.mutate({ name: trimmed, ...(description.trim() ? { description: description.trim() } : {}) });
  }

  return (
    <form onSubmit={onSubmit} noValidate className="flex max-w-sm flex-col gap-3">
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
      <div>
        <Button type="submit" loading={create.isPending}>
          Create community
        </Button>
      </div>
    </form>
  );
}

export function Onboarding() {
  const router = useRouter();
  const [needsPhone, setNeedsPhone] = useState(false);
  const telegram = useCreatorTelegram({ poll: true });
  const count = useCommunityCount();

  const connected = telegram.data?.connected === true;

  // Polls until linked, so the page updates when the creator returns from Telegram.
  useEffect(() => {
    if (connected && count.data !== undefined && count.data > 0) router.replace("/app");
  }, [connected, count.data, router]);

  if (telegram.isPending || (connected && count.isPending)) {
    return (
      <p className="flex items-center gap-2 text-ink-muted">
        <Spinner label="Loading" /> Loading your setup…
      </p>
    );
  }

  const failed = telegram.error ?? count.error;
  if (failed) {
    return (
      <Alert tone="danger" title="Couldn't load your setup.">
        {errorText(failed)}
      </Alert>
    );
  }

  return (
    <div className="flex max-w-xl flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Set up your first community</h1>
        <p className="text-ink-muted">Two quick steps. You can finish the rest from the community page.</p>
      </div>
      <ol className="flex flex-col gap-3">
        <Step number={1} title="Connect your Telegram account" done={connected} active={!connected}>
          <TelegramStep needsPhone={needsPhone} onNeedsPhone={setNeedsPhone} />
        </Step>
        <Step number={2} title="Create your community" done={false} active={connected}>
          <CommunityStep />
        </Step>
      </ol>
    </div>
  );
}
