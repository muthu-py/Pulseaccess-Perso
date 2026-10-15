import type { ButtonHTMLAttributes } from "react";

import { Spinner } from "./Spinner";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "lg" | "md" | "sm";

/** Shared look so links styled as buttons (see `buttonClass`) match real buttons exactly. */
const BASE =
  "inline-flex select-none items-center justify-center whitespace-nowrap rounded-[var(--radius-control)] font-medium transition-[background-color,border-color,color,box-shadow,transform] duration-150 active:translate-y-px disabled:cursor-not-allowed disabled:opacity-55 disabled:active:translate-y-0";

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-accent text-accent-ink border border-transparent shadow-[inset_0_1px_0_rgb(255_255_255/0.18),0_1px_2px_rgb(22_24_29/0.18)] hover:bg-accent-hover",
  secondary: "bg-surface text-ink border border-line-strong hover:border-ink-subtle hover:bg-surface-sunken",
  ghost: "bg-transparent text-ink border border-transparent hover:bg-surface-sunken",
  danger: "bg-danger text-white border border-transparent hover:brightness-95",
};

const SIZES: Record<Size, string> = {
  lg: "h-12 px-5 text-base gap-2",
  md: "h-10 px-4 text-[15px] gap-2",
  sm: "h-8 px-3 text-sm gap-1.5",
};

export function buttonClass(variant: Variant = "primary", size: Size = "md", extra = "") {
  return `${BASE} ${VARIANTS[variant]} ${SIZES[size]} ${extra}`;
}

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
  /** Shows a spinner and blocks clicks while an action is running. */
  loading?: boolean;
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  className = "",
  children,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={buttonClass(variant, size, className)}
      {...props}
    >
      {loading && <Spinner label="Working" />}
      {children}
    </button>
  );
}
