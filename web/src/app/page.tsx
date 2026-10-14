import Link from "next/link";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center gap-6 px-6 py-24">
      <p className="text-sm font-medium text-ink-muted">PulseAccess</p>
      <h1 className="text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
        Run a paid Telegram community without managing member access by hand.
      </h1>
      <p className="max-w-xl text-lg text-ink-muted">
        Create plans, take payments through Razorpay, and track each member&apos;s subscription,
        all from one creator dashboard.
      </p>
      <p className="text-sm text-ink-subtle">
        The public site is built after the app.{" "}
        <Link href="/ui" className="text-accent underline underline-offset-4">
          View the UI kit
        </Link>
        .
      </p>
    </main>
  );
}
