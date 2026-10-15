import type { Metadata } from "next";
import Link from "next/link";

import { ButtonLink, Page, Section } from "@/components/site/SiteChrome";

export const metadata: Metadata = {
  title: "How it works",
  description: "How creators set up a paid Telegram community with PulseAccess, and how members pay and subscribe.",
  alternates: { canonical: "/how-it-works" },
};

export default function HowItWorks() {
  return (
    <Page
      title="How it works"
      intro="Two sides: creators who run a community, and members who pay to join it."
    >
      <Section title="For creators">
        <ol className="flex flex-col gap-3">
          <li>
            <strong>Sign up and log in.</strong> You log in with a one-time code sent to your email. There are no
            passwords.
          </li>
          <li>
            <strong>Connect your Telegram account.</strong> Open the link PulseAccess gives you, press Start, and share
            your phone number. A phone number on your PulseAccess account is needed for this.
          </li>
          <li>
            <strong>Create a community.</strong> Give it a name and an optional description.
          </li>
          <li>
            <strong>Add the bot to your Telegram group.</strong> Make it an admin (see{" "}
            <Link href="/telegram-bot">the bot&apos;s permissions</Link>). The community page updates by itself when the bot
            is detected.
          </li>
          <li>
            <strong>Create plans.</strong> Plans can be created once the group is connected. Each has a price in rupees
            and a duration in days.
          </li>
        </ol>
      </Section>

      <Section title="For members">
        <ol className="flex flex-col gap-3">
          <li>
            <strong>Create a member account.</strong> Use your email and the phone number on your Telegram account.
          </li>
          <li>
            <strong>Connect Telegram.</strong> The phone number you share in Telegram has to match the one on your
            account.
          </li>
          <li>
            <strong>Choose a plan and pay.</strong> Payment happens on a Razorpay payment link. PulseAccess shows the
            real status of the payment and records your subscription once Razorpay confirms it.
          </li>
        </ol>
      </Section>

      <Section title="What isn't in this version">
        <p>
          Joining the Telegram group automatically after payment, and removing members when a subscription ends, are
          not part of this version yet. The dashboard does not show subscriber lists or revenue figures yet either.
        </p>
      </Section>

      <div className="flex flex-wrap gap-3">
        <ButtonLink href="/signup">Create an account</ButtonLink>
        <ButtonLink href="/faq" variant="secondary">
          Read the FAQ
        </ButtonLink>
      </div>
    </Page>
  );
}
