import type { Metadata } from "next";

import { ButtonLink } from "@/components/site/SiteChrome";
import { StatusBadge } from "@/components/ui/StatusBadge";

export const metadata: Metadata = {
  title: { absolute: "PulseAccess: sell access to your Telegram community" },
  description:
    "Create plans for your Telegram community, take payments through Razorpay, and see each member's subscription in one creator dashboard.",
  alternates: { canonical: "/" },
};

const STEPS = [
  {
    title: "Connect your Telegram",
    body: "Link the Telegram account you run your group from. It's how PulseAccess knows the group is yours.",
  },
  {
    title: "Add the bot to your group",
    body: "Make the PulseAccess bot an admin with two permissions. The dashboard shows when it's connected.",
  },
  {
    title: "Set your plans",
    body: "Name a plan, set a price in rupees and how many days it lasts. You can turn plans on and off.",
  },
  {
    title: "Members pay with Razorpay",
    body: "A member signs up, links their Telegram, picks a plan and pays through a Razorpay payment link.",
  },
];

export default function Home() {
  return (
    <>
      <section className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-6 py-20">
        <p className="text-sm font-medium text-ink-muted">For Telegram community creators</p>
        <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
          Run a paid Telegram community without managing member access by hand.
        </h1>
        <p className="max-w-2xl text-lg text-ink-muted">
          Create plans, take payments through Razorpay, and track each member&apos;s subscription, all from one
          creator dashboard.
        </p>
        <div className="flex flex-wrap gap-3">
          <ButtonLink href="/signup">Create an account</ButtonLink>
          <ButtonLink href="/how-it-works" variant="secondary">
            See how it works
          </ButtonLink>
        </div>
      </section>

      <section aria-labelledby="steps-heading" className="border-y border-line bg-surface">
        <div className="mx-auto flex max-w-5xl flex-col gap-8 px-6 py-14">
          <h2 id="steps-heading" className="text-2xl font-semibold tracking-tight">
            From sign-up to first payment
          </h2>
          <ol className="grid gap-6 sm:grid-cols-2">
            {STEPS.map((step, i) => (
              <li key={step.title} className="flex gap-4">
                <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-accent-soft text-sm font-medium text-ink">
                  {i + 1}
                </span>
                <div className="flex flex-col gap-1">
                  <h3 className="font-medium">{step.title}</h3>
                  <p className="text-ink-muted">{step.body}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section aria-labelledby="status-heading" className="mx-auto flex w-full max-w-5xl flex-col gap-4 px-6 py-14">
        <h2 id="status-heading" className="text-2xl font-semibold tracking-tight">
          Status you can trust
        </h2>
        <p className="max-w-2xl text-ink-muted">
          Connection and payment status always come from PulseAccess itself, never from a button you clicked. These
          are the states you&apos;ll see in the dashboard.
        </p>
        <div className="flex flex-col gap-3 rounded-[var(--radius-card)] border border-line bg-surface p-5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="w-36 text-sm font-medium text-ink-muted">Telegram group</span>
            <StatusBadge kind="connection" value="NOT_CONNECTED" />
            <StatusBadge kind="connection" value="CONNECTED" />
            <StatusBadge kind="connection" value="NEEDS_ATTENTION" />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="w-36 text-sm font-medium text-ink-muted">Payment</span>
            <StatusBadge kind="payment" value="created" />
            <StatusBadge kind="payment" value="paid" />
            <StatusBadge kind="payment" value="expired" />
          </div>
        </div>
      </section>
    </>
  );
}
