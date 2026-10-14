"use client";

import { useId, type InputHTMLAttributes, type ReactNode } from "react";

export type TextFieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, "id"> & {
  label: string;
  hint?: ReactNode;
  error?: string;
  /** Text shown before the input, e.g. "₹". */
  prefix?: string;
};

export function TextField({ label, hint, error, prefix, className = "", ...props }: TextFieldProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [errorId, hintId].filter(Boolean).join(" ") || undefined;

  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      <label htmlFor={id} className="text-sm font-medium text-ink">
        {label}
        {props.required && <span className="text-ink-subtle"> (required)</span>}
      </label>
      <div
        className={`flex h-10 items-center rounded-[var(--radius-control)] border bg-surface focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-[var(--focus-ring)] ${
          error ? "border-danger" : "border-line-strong"
        }`}
      >
        {prefix && <span className="pl-3 text-ink-muted">{prefix}</span>}
        <input
          id={id}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className="h-full w-full min-w-0 bg-transparent px-3 text-[15px] text-ink outline-none placeholder:text-ink-subtle"
          {...props}
        />
      </div>
      {error && (
        <p id={errorId} className="text-sm text-danger">
          {error}
        </p>
      )}
      {hint && (
        <p id={hintId} className="text-sm text-ink-muted">
          {hint}
        </p>
      )}
    </div>
  );
}
