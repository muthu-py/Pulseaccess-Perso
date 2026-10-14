"use client";

import { useEffect, useRef, type ReactNode } from "react";

import { Button } from "./Button";

/** Modal confirmation. Escape or Cancel closes it; focus starts on Cancel so a stray Enter is safe. */
export function ConfirmDialog({
  title,
  children,
  confirmLabel,
  danger = false,
  busy = false,
  onConfirm,
  onCancel,
}: {
  title: string;
  children: ReactNode;
  confirmLabel: string;
  danger?: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    cancelRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCancel]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        className="flex w-full max-w-md flex-col gap-4 rounded-[var(--radius-card)] border border-line bg-surface p-6"
      >
        <h2 id="confirm-title" className="text-lg font-semibold">
          {title}
        </h2>
        <div className="text-ink-muted">{children}</div>
        <div className="flex justify-end gap-2">
          <button
            ref={cancelRef}
            type="button"
            onClick={onCancel}
            disabled={busy}
            className="h-10 rounded-[var(--radius-control)] border border-line-strong bg-surface px-4 text-[15px] font-medium hover:bg-surface-sunken disabled:opacity-55"
          >
            Cancel
          </button>
          <Button variant={danger ? "danger" : "primary"} onClick={onConfirm} loading={busy}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
