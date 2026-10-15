import type { Metadata } from "next";
import type { ReactNode } from "react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { TextField } from "@/components/ui/TextField";
import { KNOWN_STATUSES, type StatusKind } from "@/lib/status";

export const metadata: Metadata = {
  title: "UI kit",
  robots: { index: false, follow: false },
};

const SWATCHES = [
  "canvas", "surface", "surface-sunken", "ink", "ink-muted", "line-strong",
  "accent", "accent-soft", "success", "warning", "danger", "info",
];

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-4 border-t border-line pt-8">
      <h2 className="text-xl font-semibold">{title}</h2>
      {children}
    </section>
  );
}

export default function UiKit() {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-10 px-6 py-12">
      <header className="flex flex-col gap-2">
        <p className="text-sm font-medium text-ink-muted">Internal · not indexed</p>
        <h1 className="text-4xl font-semibold tracking-tight">PulseAccess UI kit</h1>
        <p className="text-ink-muted">
          Tokens and components shared by the public site and the app. Toggle your OS dark mode
          to check both themes.
        </p>
      </header>

      <Section title="Colour tokens">
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
          {SWATCHES.map((name) => (
            <li key={name} className="flex flex-col gap-2">
              <span
                className="h-12 rounded-[var(--radius-control)] border border-line"
                style={{ background: `var(--${name})` }}
              />
              <code className="font-mono text-xs text-ink-muted">--{name}</code>
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Type scale">
        <p className="text-5xl font-semibold tracking-tight">Display 48</p>
        <p className="text-4xl font-semibold tracking-tight">Section heading 36</p>
        <p className="text-xl font-semibold">Card heading 20</p>
        <p className="max-w-[68ch] text-base">
          Body 16. Add the PulseAccess bot to your Telegram group as an administrator. PulseAccess
          checks its permissions before marking the community as connected.
        </p>
        <p className="text-[13px] text-ink-muted">Label 13 · supporting detail</p>
        <p className="font-mono text-sm">-1001234567890 · plink_TnnmzWP6rLD8t5</p>
      </Section>

      <Section title="Buttons">
        <div className="flex flex-wrap items-center gap-3">
          <Button>Create community</Button>
          <Button variant="secondary">Cancel</Button>
          <Button variant="ghost">Edit</Button>
          <Button variant="danger">Deactivate</Button>
          <Button loading>Saving</Button>
          <Button disabled>Disabled</Button>
          <Button size="sm">Small</Button>
        </div>
      </Section>

      <Section title="Fields">
        <div className="grid max-w-xl gap-5">
          <TextField label="Community name" placeholder="Java Masters" required />
          <TextField label="Price" prefix="₹" inputMode="decimal" placeholder="499" hint="Charged per period. Minimum ₹1." />
          <TextField label="Phone" defaultValue="98765" error="Include the country code, e.g. +919876543210." />
        </div>
      </Section>

      <Section title="Status badges">
        {(Object.keys(KNOWN_STATUSES) as StatusKind[]).map((kind) => (
          <div key={kind} className="flex flex-col gap-2">
            <p className="text-sm font-medium capitalize text-ink-muted">{kind}</p>
            <div className="flex flex-wrap gap-2">
              {KNOWN_STATUSES[kind].map((value) => (
                <StatusBadge key={value} kind={kind} value={value} />
              ))}
            </div>
          </div>
        ))}
      </Section>

      <Section title="Alerts">
        <div className="grid max-w-2xl gap-3">
          <Alert tone="success" title="Group connected">
            “Java Masters” can now sell plans.
          </Alert>
          <Alert tone="warning" title="The bot needs admin rights">
            Make @pulse_access_2_bot an administrator with “Invite users via link” and “Ban users”.
          </Alert>
          <Alert tone="danger" title="Couldn&apos;t create the payment link">
            Razorpay didn&apos;t respond. Try again in a moment.
          </Alert>
          <Alert tone="info">Payment links expire after 30 minutes.</Alert>
        </div>
      </Section>
    </main>
  );
}
