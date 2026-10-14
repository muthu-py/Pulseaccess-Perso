import type { Metadata } from "next";

import { Page, Section } from "@/components/site/SiteChrome";

export const metadata: Metadata = {
  title: "The Telegram bot",
  description: "What the PulseAccess bot needs in your Telegram group, which permissions it asks for, and why.",
  alternates: { canonical: "/telegram-bot" },
};

export default function TelegramBot() {
  return (
    <Page
      title="The Telegram bot"
      intro="The bot connects your Telegram group to your PulseAccess community. It needs to be an admin, with two permissions."
    >
      <Section title="Permissions it asks for">
        <ul>
          <li>
            <strong>Invite users via link.</strong> Needed to handle people joining through your community&apos;s
            invite link.
          </li>
          <li>
            <strong>Ban users.</strong> Needed to remove someone from the group when their access should end.
          </li>
        </ul>
        <p>It does not need any other admin permission.</p>
      </Section>

      <Section title="How to add it">
        <ol className="flex flex-col gap-2">
          <li>Connect your own Telegram account in PulseAccess first. The bot only accepts a group from you.</li>
          <li>Open your Telegram group and add the PulseAccess bot as a member.</li>
          <li>Make it an admin and turn on the two permissions above.</li>
          <li>Go back to your community page. It shows <strong>Connected</strong> once PulseAccess detects the bot.</li>
        </ol>
      </Section>

      <Section title="If it shows “Needs attention”">
        <p>
          The bot was removed from the group, or one of the two permissions was turned off. Check that it&apos;s still in
          the group and an admin with both permissions. The status clears by itself once it&apos;s fixed.
        </p>
      </Section>
    </Page>
  );
}
