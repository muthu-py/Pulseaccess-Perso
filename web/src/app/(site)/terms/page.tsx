import type { Metadata } from "next";

import { Alert } from "@/components/ui/Alert";
import { Page, Section } from "@/components/site/SiteChrome";

export const metadata: Metadata = {
  title: "Terms",
  description: "The terms for using PulseAccess as a creator or a member.",
  alternates: { canonical: "/terms" },
};

export default function Terms() {
  return (
    <Page title="Terms" intro="The basic rules for using PulseAccess.">
      <Alert tone="warning" title="Draft: not yet reviewed by a lawyer.">
        These terms describe how the product works today. They must be reviewed and completed by the operator of the
        service before launch.
      </Alert>

      <Section title="Accounts">
        <p>
          You are responsible for the account you create and for the email address you use to log in. Keep your login
          codes private.
        </p>
      </Section>

      <Section title="Creators">
        <p>
          You are responsible for your community, its content, the plans you offer and what you promise members.
          PulseAccess provides the tools to create plans and record payments and subscriptions.
        </p>
      </Section>

      <Section title="Members">
        <p>
          A payment pays for the plan you chose, for the duration shown on that plan. Payments are processed by
          Razorpay and are subject to Razorpay&apos;s terms.
        </p>
      </Section>

      <Section title="Availability">
        <p>
          PulseAccess depends on Telegram and Razorpay. If either is unavailable, parts of PulseAccess may not work.
        </p>
      </Section>
    </Page>
  );
}
