"use client";

import { useId, type InputHTMLAttributes, type ReactNode } from "react";

export type TextFieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, "id" | "prefix"> & {
  label: string;
  hint?: ReactNode;
  error?: string;
  /** Text shown before the input, e.g. "₹". */
  prefix?: string;
  /** Text shown after the input, e.g. "days". */
  suffix?: string;
};

const NO_SPELLCHECK = new Set(["email", "tel"]);

export function TextField({ label, hint, error, prefix, suffix, className = "", ...props }: TextFieldProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [errorId, hintId].filter(Boolean).join(" ") || undefined;
  const spellCheck = props.spellCheck ?? (NO_SPELLCHECK.has(String(props.type)) ? false : undefined);

  return (
    <div className={`flex min-w-0 flex-col gap-1.5 ${className}`}>
      <label htmlFor={id} className="text-sm font-medium text-ink">
        {label}
        {props.required && <span className="font-normal text-ink-subtle"> (required)</span>}
      </label>
      <div
        className={`flex h-11 items-center rounded-[var(--radius-control)] border bg-surface transition-[border-color,box-shadow] duration-150 focus-within:border-accent focus-within:shadow-[0_0_0_3px_var(--accent-soft)] ${
          error ? "border-danger" : "border-line-strong hover:border-ink-subtle"
        }`}
      >
        {prefix && <span className="pl-3 text-ink-muted">{prefix}</span>}
        <input
          id={id}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          spellCheck={spellCheck}
          className="h-full w-full min-w-0 bg-transparent px-3 text-[15px] text-ink outline-none placeholder:text-ink-subtle"
          {...props}
        />
        {suffix && <span className="pr-3 text-sm text-ink-muted">{suffix}</span>}
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
