import type { Metadata } from "next";
import Link from "next/link";

import { Alert } from "@/components/ui/Alert";
import { Page, Section } from "@/components/site/SiteChrome";

export const metadata: Metadata = {
  title: "Privacy",
  description: "What personal information PulseAccess collects, why, and who it is shared with.",
  alternates: { canonical: "/privacy" },
};

export default function Privacy() {
  return (
    <Page title="Privacy" intro="What PulseAccess collects and why, in plain language.">
      <Alert tone="warning" title="Draft: not yet reviewed by a lawyer.">
        This page describes what the product does today. It must be reviewed and completed by the operator of the
        service before launch.
      </Alert>

      <Section title="What we collect">
        <ul>
          <li>
            <strong>Creators:</strong> name, username, email, and phone number if you add one.
          </li>
          <li>
            <strong>Members:</strong> name, email and phone number.
          </li>
          <li>
            <strong>Telegram:</strong> when you connect Telegram, your Telegram account ID and username, and the
            Telegram group your community is linked to.
          </li>
          <li>
            <strong>Payments:</strong> the plan, amount and status of each payment, and subscription start and end
            dates. Card and bank details are handled by Razorpay and are not stored by PulseAccess.
          </li>
        </ul>
      </Section>

      <Section title="Why we use it">
        <p>
          To run your account, log you in with one-time codes, match your Telegram account to your PulseAccess account,
          and record payments and subscriptions.
        </p>
      </Section>

      <Section title="Who it is shared with">
        <p>
          Razorpay processes payments. Telegram is used to connect accounts and groups. Creators can see information
          about their own community and its plans.
        </p>
      </Section>

      <Section title="Cookies and storage">
        <p>
          Creators receive a secure, HttpOnly cookie that keeps them logged in. Access tokens are kept in memory only,
          so members need to log in again after reloading the page.
        </p>
      </Section>

      <Section title="Questions">
        <p>
          Use the <Link href="/contact">contact page</Link>.
        </p>
      </Section>
    </Page>
  );
}
