"use client";

import { useEffect, useState, useSyncExternalStore } from "react";

import { Icon } from "@/components/ui/icons";

/**
 * A replay of the real product moment, built from the same states the app shows:
 * the bot gets admin rights, the group connects, the plan goes on sale, a member pays.
 * Example data, clearly labelled. Static final state under reduced motion.
 */
const STAGES = 5;
const STEP_MS = 2200;

function useReducedMotion() {
  return useSyncExternalStore(
    (cb) => {
      const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
      mq.addEventListener("change", cb);
      return () => mq.removeEventListener("change", cb);
    },
    () => window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    () => false,
  );
}

export function HeroDemo() {
  const reduced = useReducedMotion();
  const [tick, setTick] = useState(0);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (reduced || paused) return;
    const id = window.setInterval(() => setTick((t) => (t + 1) % (STAGES + 1)), STEP_MS);
    return () => window.clearInterval(id);
  }, [reduced, paused]);

  const stage = reduced ? STAGES : tick;
  const invite = stage >= 1;
  const ban = stage >= 2;
  const connected = stage >= 3;
  const paid = stage >= 5;

  return (
    <figure className="relative flex min-w-0 flex-col gap-3">
      <div className="rounded-[22px] bg-night p-3 text-night-ink shadow-[var(--shadow-raised)] sm:p-4">
        {/* Window bar */}
        <div className="flex items-center justify-between px-2 pb-3 pt-1 text-xs text-night-muted">
          <span>Example community</span>
          {!reduced && (
            <button
              type="button"
              onClick={() => setPaused((p) => !p)}
              className="rounded-md px-2 py-1 text-night-muted transition-colors hover:bg-night-raised hover:text-night-ink"
              aria-label={paused ? "Play the demo" : "Pause the demo"}
            >
              {paused ? "Play" : "Pause"}
            </button>
          )}
        </div>

        <div className="flex flex-col gap-3 rounded-[16px] bg-night-raised p-4 sm:p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="font-display text-xl font-semibold">Option Traders Circle</p>
            <span
              className={`inline-flex h-6 items-center gap-1.5 rounded-full px-2.5 text-[13px] font-medium transition-colors duration-500 ${
                connected ? "bg-[#1d3b2a] text-[#7fe0a6]" : "bg-[#2a2d35] text-night-muted"
              }`}
            >
              {connected ? <Icon name="check" /> : <span className="pulse-dot text-[#8b97ff]" aria-hidden="true" />}
              {connected ? "Connected" : "Waiting for the bot"}
            </span>
          </div>

          {/* Telegram's own admin rights screen, as the creator sees it */}
          <div className="flex flex-col divide-y divide-night-line rounded-xl border border-night-line text-sm">
            <Toggle label="Invite users via link" on={invite} />
            <Toggle label="Ban users" on={ban} />
          </div>

          <p className={`text-xs text-night-muted transition-opacity duration-500 ${connected ? "opacity-100" : "opacity-0"}`}>
            Group chat ID <span className="font-mono text-night-ink">-1002193840571</span>
          </p>
        </div>

        {/* The pass: the product's one bold object */}
        <div
          className={`pass-notch mt-3 flex items-end justify-between gap-4 rounded-[var(--radius-pass)] bg-pass p-5 text-pass-ink transition-transform duration-700 ${
            stage >= 4 ? "translate-y-0" : "translate-y-1.5"
          }`}
          style={{ ["--notch-y" as string]: "58%" }}
        >
          <div className="flex flex-col gap-0.5">
            <p className="text-sm font-medium">Monthly</p>
            <p className="font-display text-4xl font-semibold tabular leading-none">₹499</p>
            <p className="text-sm">30 days of access</p>
          </div>
          <span
            className={`inline-flex h-7 items-center gap-1.5 rounded-full px-3 text-[13px] font-medium transition-colors duration-500 ${
              paid ? "bg-pass-ink text-pass" : "border border-pass-ink/40 text-pass-ink"
            }`}
          >
            {paid ? <Icon name="check" /> : <Icon name="clock" />}
            {paid ? "Paid" : stage >= 4 ? "Awaiting payment" : "On sale soon"}
          </span>
        </div>
      </div>
      <figcaption className="px-1 text-sm text-ink-subtle">
        Example data. The states are the ones the dashboard shows, in order.
      </figcaption>
    </figure>
  );
}

function Toggle({ label, on }: { label: string; on: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3 px-3.5 py-3">
      <span>{label}</span>
      <span
        aria-hidden="true"
        className={`relative h-5 w-9 shrink-0 rounded-full transition-colors duration-300 ${on ? "bg-[#4f9cf0]" : "bg-[#3a3d46]"}`}
      >
        <span
          className={`absolute top-0.5 size-4 rounded-full bg-white transition-transform duration-300 ${on ? "translate-x-[18px]" : "translate-x-0.5"}`}
        />
      </span>
      <span className="sr-only">{on ? "on" : "off"}</span>
    </div>
  );
}
