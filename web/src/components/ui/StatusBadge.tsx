import { statusView, type StatusKind, type Tone } from "@/lib/status";

import { Icon } from "./icons";

const TONES: Record<Tone, string> = {
  success: "bg-success-soft text-success",
  warning: "bg-warning-soft text-warning",
  danger: "bg-danger-soft text-danger",
  info: "bg-info-soft text-info",
  neutral: "bg-neutral-soft text-neutral",
};

export function StatusBadge({
  kind,
  value,
  label,
}: {
  kind: StatusKind;
  value: string | null | undefined;
  /** Override the default label, e.g. "Active until 13 Nov". */
  label?: string;
}) {
  const view = statusView(kind, value);
  return (
    <span
      data-tone={view.tone}
      className={`inline-flex h-6 items-center gap-1.5 rounded-full px-2.5 text-[13px] font-medium ${TONES[view.tone]}`}
    >
      <Icon name={view.icon} />
      {label ?? view.label}
    </span>
  );
}
