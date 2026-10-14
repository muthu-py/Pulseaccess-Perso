import type { Metadata } from "next";

export const metadata: Metadata = { title: "Settings" };

export default function SettingsPage() {
  return (
    <div className="flex max-w-xl flex-col gap-2">
      <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
      <p className="text-ink-muted">Account settings come in a later step.</p>
    </div>
  );
}
