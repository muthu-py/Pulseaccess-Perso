import type { ReactNode } from "react";

import type { Tone } from "@/lib/status";

import { Icon } from "./icons";

const TONES: Record<Tone, { box: string; icon: "check" | "alert" | "info" | "x" }> = {
  success: { box: "border-success/30 bg-success-soft", icon: "check" },
  warning: { box: "border-warning/30 bg-warning-soft", icon: "alert" },
  danger: { box: "border-danger/30 bg-danger-soft", icon: "alert" },
  info: { box: "border-info/30 bg-info-soft", icon: "info" },
  neutral: { box: "border-line bg-surface-sunken", icon: "info" },
};

export function Alert({
  tone = "info",
  title,
  children,
}: {
  tone?: Tone;
  title?: string;
  children?: ReactNode;
}) {
  const t = TONES[tone];
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      className={`flex gap-3 rounded-[var(--radius-card)] border p-4 text-sm text-ink ${t.box}`}
    >
      <Icon name={t.icon} width={16} height={16} className="mt-0.5 shrink-0" />
      <div className="flex flex-col gap-1">
        {title && <p className="font-medium">{title}</p>}
        {children && <div className="text-ink-muted">{children}</div>}
      </div>
    </div>
  );
}
