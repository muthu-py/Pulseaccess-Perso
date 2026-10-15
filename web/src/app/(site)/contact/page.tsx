import type { Metadata } from "next";

import { Page, Section } from "@/components/site/SiteChrome";

export const metadata: Metadata = {
  title: "Contact",
  description: "How to get in touch with the PulseAccess team.",
  alternates: { canonical: "/contact" },
};

export default function Contact() {
  const email = process.env.NEXT_PUBLIC_CONTACT_EMAIL;

  return (
    <Page title="Contact">
      <Section title="Email">
        {email ? (
          <p>
            Write to <a href={`mailto:${email}`}>{email}</a>.
          </p>
        ) : (
          <p>A contact address hasn&apos;t been set up yet.</p>
        )}
      </Section>
      <Section title="Before you write">
        <p>
          For a payment, include the payment ID from the payment page. For a Telegram connection problem, say whether
          you are a creator or a member.
        </p>
      </Section>
    </Page>
  );
}
