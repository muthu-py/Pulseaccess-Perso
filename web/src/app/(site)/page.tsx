import type { Metadata } from "next";
import Link from "next/link";

import { HeroDemo } from "@/components/site/HeroDemo";
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
    body: "Link the Telegram account you run your group from. That's how PulseAccess knows the group is yours.",
  },
  {
    title: "Add the bot as admin",
    body: "Two permissions: invite users via link, and ban users. The dashboard says Connected when it sees the bot.",
  },
  {
    title: "Put plans on sale",
    body: "A name, a price in rupees and a number of days. Turn plans on and off whenever you like.",
  },
  {
    title: "Members pay with Razorpay",
    body: "They sign up, link their Telegram, pick a plan and pay on a Razorpay link. You see the payment land.",
  },
];

export default function Home() {
  return (
    <>
      <section className="mx-auto grid w-full max-w-6xl items-center gap-12 px-5 pb-20 pt-14 sm:px-8 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)] lg:gap-16 lg:pt-20">
        <div className="flex min-w-0 flex-col gap-7">
          <h1 className="text-[2.75rem] font-semibold leading-[0.98] sm:text-6xl lg:text-[4.25rem]">
            Your Telegram group, with a price on the door.
          </h1>
          <p className="max-w-[34rem] text-lg leading-relaxed text-ink-muted sm:text-xl">
            Set plans in rupees, take payments through Razorpay, and see who has paid. PulseAccess works with your
            group through a bot you add as admin.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <ButtonLink href="/signup" size="lg">
              Create a creator account
            </ButtonLink>
            <ButtonLink href="/how-it-works" variant="secondary" size="lg">
              See how it works
            </ButtonLink>
          </div>
          <p className="text-sm text-ink-muted">
            Joining a community?{" "}
            <Link href="/m/login" className="font-medium text-ink underline decoration-line-strong underline-offset-4 hover:decoration-ink">
              Member log in
            </Link>
          </p>
        </div>
        <HeroDemo />
      </section>

      <section aria-labelledby="setup-heading" className="border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-col gap-10 px-5 py-20 sm:px-8">
          <div className="flex max-w-2xl flex-col gap-3">
            <h2 id="setup-heading" className="text-3xl font-semibold sm:text-4xl">
              From sign-up to the first payment
            </h2>
            <p className="text-lg text-ink-muted">Four steps, in this order. Each one unlocks the next.</p>
          </div>
          <ol className="grid gap-x-8 gap-y-10 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((step, i) => (
              <li key={step.title} className="flex flex-col gap-3 border-t-2 border-ink pt-5">
                <span className="font-display text-sm font-semibold tabular text-ink-subtle">Step {i + 1}</span>
                <h3 className="text-xl font-semibold">{step.title}</h3>
                <p className="text-ink-muted">{step.body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section aria-labelledby="truth-heading" className="border-t border-line bg-surface">
        <div className="mx-auto grid max-w-6xl gap-10 px-5 py-20 sm:px-8 lg:grid-cols-2 lg:gap-16">
          <div className="flex flex-col gap-4">
            <h2 id="truth-heading" className="text-3xl font-semibold sm:text-4xl">
              Status that comes from the source
            </h2>
            <p className="text-lg text-ink-muted">
              PulseAccess never marks a group connected or a payment paid because someone clicked a button. It waits
              for Telegram and Razorpay to say so, then updates the page by itself.
            </p>
            <Link href="/telegram-bot" className="w-fit font-medium text-accent underline underline-offset-4 hover:text-accent-hover">
              What the bot needs in your group
            </Link>
          </div>
          <dl className="flex flex-col divide-y divide-line rounded-[var(--radius-card)] border border-line">
            <StatusRow term="Telegram group">
              <StatusBadge kind="connection" value="NOT_CONNECTED" />
              <StatusBadge kind="connection" value="CONNECTED" />
              <StatusBadge kind="connection" value="NEEDS_ATTENTION" />
            </StatusRow>
            <StatusRow term="Payment">
              <StatusBadge kind="payment" value="created" />
              <StatusBadge kind="payment" value="paid" />
              <StatusBadge kind="payment" value="expired" />
            </StatusRow>
            <StatusRow term="Subscription">
              <StatusBadge kind="subscription" value="active" />
              <StatusBadge kind="subscription" value="expired" />
            </StatusRow>
          </dl>
        </div>
      </section>

      <section className="bg-night text-night-ink">
        <div className="mx-auto flex max-w-6xl flex-col items-start gap-6 px-5 py-20 sm:px-8 md:flex-row md:items-end md:justify-between">
          <div className="flex max-w-xl flex-col gap-3">
            <h2 className="text-3xl font-semibold sm:text-4xl">Set up your first community today.</h2>
            <p className="text-lg text-night-muted">You need an email address, a phone number and a Telegram group.</p>
          </div>
          <Link
            href="/signup"
            className="inline-flex h-12 items-center rounded-[var(--radius-control)] bg-pass px-5 text-base font-medium text-pass-ink transition-[filter] hover:brightness-95"
          >
            Create a creator account
          </Link>
        </div>
      </section>
    </>
  );
}

function StatusRow({ term, children }: { term: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:gap-6">
      <dt className="w-32 shrink-0 text-sm font-medium text-ink">{term}</dt>
      <dd className="flex flex-wrap gap-2">{children}</dd>
    </div>
  );
}
