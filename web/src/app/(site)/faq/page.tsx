import type { Metadata } from "next";

import { Page } from "@/components/site/SiteChrome";

export const metadata: Metadata = {
  title: "FAQ",
  description: "Answers to common questions about PulseAccess: logging in, payments, plans and the Telegram bot.",
  alternates: { canonical: "/faq" },
};

const QUESTIONS: { q: string; a: string }[] = [
  {
    q: "How do I log in?",
    a: "With a one-time code sent to your email. PulseAccess has no passwords. Codes expire after 5 minutes, and a code stops working after too many wrong attempts.",
  },
  {
    q: "Why does PulseAccess ask for my phone number?",
    a: "To match your Telegram account to your PulseAccess account. The phone number you share with the bot in Telegram has to match the one on your account.",
  },
  {
    q: "Who handles payments?",
    a: "Razorpay. Members pay on a Razorpay payment link, and PulseAccess records the payment once Razorpay confirms it. PulseAccess does not see card details.",
  },
  {
    q: "What happens if a payment link expires?",
    a: "Nothing is charged. The member goes back to the community page and chooses the plan again to get a new link.",
  },
  {
    q: "Does PulseAccess add paying members to my Telegram group automatically?",
    a: "Not in this version. Subscriptions are recorded after payment, but automatic joining and removal are not available yet.",
  },
  {
    q: "Why can't I create a plan?",
    a: "Plans can be created once the community's Telegram group is connected. Add the bot to your group as an admin and the community page will show Connected.",
  },
  {
    q: "Can I deactivate a community or a plan?",
    a: "Yes. Both can be deactivated and activated again from your dashboard.",
  },
  {
    q: "How much does PulseAccess cost?",
    a: "There is no published pricing yet.",
  },
];

export default function Faq() {
  return (
    <Page title="Frequently asked questions" intro="Logging in, payments, plans and the Telegram bot.">
      <dl className="flex flex-col divide-y divide-line border-y border-line">
        {QUESTIONS.map(({ q, a }) => (
          <div key={q} className="flex flex-col gap-2 py-6">
            <dt className="font-display text-xl font-semibold text-ink">{q}</dt>
            <dd className="text-[17px] leading-relaxed text-ink-muted">{a}</dd>
          </div>
        ))}
      </dl>
    </Page>
  );
}
