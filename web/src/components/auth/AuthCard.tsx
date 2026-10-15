import type { ReactNode } from "react";

import { Logo } from "@/components/ui/Brand";

const ASIDE = {
  creator: {
    heading: "Run the paid side of your Telegram group.",
    points: [
      "Log in with a code sent to your email. No passwords.",
      "Connect your Telegram account, then add the bot to your group.",
      "Put plans on sale in rupees. Members pay through Razorpay.",
    ],
  },
  member: {
    heading: "Join a paid Telegram community.",
    points: [
      "Log in with a code sent to your email. No passwords.",
      "Link the Telegram account that has your phone number.",
      "Pick a plan and pay on a Razorpay link.",
    ],
  },
};

/** Split layout for sign-in pages: the form, and what happens after it. */
export function AuthCard({
  title,
  subtitle,
  audience = "creator",
  children,
}: {
  title: string;
  subtitle?: string;
  audience?: "creator" | "member";
  children: ReactNode;
}) {
  const aside = ASIDE[audience];
  return (
    <div className="grid flex-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)]">
      <main id="main" className="flex flex-col px-5 py-8 sm:px-10">
        <Logo />
        <div className="mx-auto flex w-full max-w-[26rem] flex-1 flex-col justify-center gap-7 py-12">
          <div className="flex flex-col gap-2">
            <h1 className="text-[2rem] font-semibold leading-tight">{title}</h1>
            {subtitle && <p className="text-ink-muted">{subtitle}</p>}
          </div>
          {children}
        </div>
      </main>

      <aside className="relative hidden overflow-hidden bg-night p-12 text-night-ink lg:flex lg:flex-col lg:justify-end">
        <div
          aria-hidden="true"
          className="pass-notch absolute -right-16 top-16 h-56 w-96 rotate-[-8deg] rounded-[var(--radius-pass)] bg-pass opacity-95"
          style={{ ["--notch-y" as string]: "50%" }}
        />
        <div
          aria-hidden="true"
          className="pass-notch absolute -right-4 top-52 h-56 w-96 rotate-[4deg] rounded-[var(--radius-pass)] bg-pass-deep opacity-70"
          style={{ ["--notch-y" as string]: "50%" }}
        />
        <div className="relative flex max-w-md flex-col gap-6">
          <p className="font-display text-3xl font-semibold leading-tight">{aside.heading}</p>
          <ol className="flex flex-col gap-4 text-night-muted">
            {aside.points.map((point, i) => (
              <li key={point} className="flex gap-3">
                <span className="flex size-6 shrink-0 items-center justify-center rounded-full border border-night-line text-xs tabular text-night-ink">
                  {i + 1}
                </span>
                <span>{point}</span>
              </li>
            ))}
          </ol>
        </div>
      </aside>
    </div>
  );
}
