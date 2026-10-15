export type Tone = "success" | "warning" | "danger" | "info" | "neutral";
export type StatusIcon = "check" | "alert" | "clock" | "x" | "dot";
export type StatusKind = "connection" | "payment" | "subscription";

export type StatusView = { label: string; tone: Tone; icon: StatusIcon };

/** Every backend value the UI knows how to show, per kind. */
export const KNOWN_STATUSES: Record<StatusKind, string[]> = {
  connection: ["NOT_CONNECTED", "CONNECTING", "CONNECTED", "NEEDS_ATTENTION", "DISCONNECTED"],
  payment: ["created", "paid", "expired", "cancelled"],
  subscription: ["active", "expired", "cancelled"],
};

const VIEWS: Record<StatusKind, Record<string, StatusView>> = {
  connection: {
    NOT_CONNECTED: { label: "Not connected", tone: "neutral", icon: "dot" },
    CONNECTING: { label: "Connecting", tone: "info", icon: "clock" },
    CONNECTED: { label: "Connected", tone: "success", icon: "check" },
    NEEDS_ATTENTION: { label: "Needs attention", tone: "warning", icon: "alert" },
    DISCONNECTED: { label: "Disconnected", tone: "danger", icon: "x" },
  },
  payment: {
    created: { label: "Awaiting payment", tone: "info", icon: "clock" },
    paid: { label: "Paid", tone: "success", icon: "check" },
    expired: { label: "Expired", tone: "neutral", icon: "x" },
    cancelled: { label: "Cancelled", tone: "neutral", icon: "x" },
  },
  subscription: {
    active: { label: "Active", tone: "success", icon: "check" },
    expired: { label: "Expired", tone: "neutral", icon: "x" },
    cancelled: { label: "Cancelled", tone: "neutral", icon: "x" },
  },
};

const UNKNOWN: StatusView = { label: "Unknown", tone: "neutral", icon: "dot" };

/** Maps a backend status to label, tone and icon. Unknown values never throw. */
export function statusView(kind: StatusKind, value: string | null | undefined): StatusView {
  if (!value) return UNKNOWN;
  return VIEWS[kind][value] ?? { ...UNKNOWN, label: value };
}
