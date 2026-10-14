import type { ReactNode } from "react";

export function PageHeader({
  title,
  description,
  actions,
  meta,
}: {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  /** Small row under the title, e.g. status badges. */
  meta?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="flex min-w-0 flex-col gap-2">
        <h1 className="break-words text-3xl font-semibold leading-tight sm:text-[2.25rem]">{title}</h1>
        {meta && <div className="flex flex-wrap items-center gap-2">{meta}</div>}
        {description && <p className="max-w-2xl text-ink-muted">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

/** Placeholder for an empty list: says what goes here and how to add the first one. */
export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-[var(--radius-card)] border border-dashed border-line-strong px-6 py-10 sm:items-center sm:text-center">
      <svg width="56" height="40" viewBox="0 0 56 40" aria-hidden="true" focusable="false" className="text-line-strong">
        <rect x="2" y="6" width="52" height="28" rx="7" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="4 4" />
        <circle cx="28" cy="20" r="4" fill="var(--pass)" />
      </svg>
      <p className="font-display text-lg font-semibold text-ink">{title}</p>
      {children && <div className="max-w-md text-ink-muted">{children}</div>}
      {action}
    </div>
  );
}

export function LoadingRow({ label = "Loading…" }: { label?: string }) {
  return (
    <p role="status" className="flex items-center gap-2.5 py-6 text-ink-muted">
      <span className="pulse-dot text-ink-subtle" aria-hidden="true" />
      {label}
    </p>
  );
}
