"use client";

import { useState, useSyncExternalStore } from "react";
import { Button } from "@/components/ui/Button";

interface ShareLinkProps {
  communityId: string;
  communityName: string;
  isConnected: boolean;
  isActive: boolean;
}

const noopSubscribe = () => () => {};

export function ShareLink({
  communityId,
  communityName,
  isConnected,
  isActive,
}: ShareLinkProps) {
  const [copied, setCopied] = useState(false);
  const origin = useSyncExternalStore(
    noopSubscribe,
    () => (typeof window !== "undefined" ? window.location.origin : ""),
    () => "",
  );

  const memberPath = `/c/${communityId}`;
  const fullUrl = origin ? `${origin}${memberPath}` : memberPath;

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(fullUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback if clipboard API is blocked
      setCopied(false);
    }
  }

  return (
    <section
      aria-labelledby="share-link-heading"
      className="flex flex-col gap-4 rounded-[var(--radius-card)] border border-line bg-surface p-5 sm:p-6"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <svg
            className="size-5 text-accent"
            viewBox="0 0 20 20"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
          </svg>
          <h2 id="share-link-heading" className="text-lg font-semibold text-ink">
            Member invite link
          </h2>
        </div>
        <span className="text-xs text-ink-muted">Direct subscriber access</span>
      </div>

      <p className="text-sm text-ink-muted leading-relaxed">
        Share this link with prospective members on Telegram, X, or your website. Members use this
        link to log in, view plans for <strong className="font-medium text-ink">{communityName}</strong>, pay via
        Razorpay, and get automatically invited to the Telegram group.
      </p>

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <div className="relative flex-1 min-w-0">
          <input
            type="text"
            readOnly
            value={fullUrl}
            aria-label="Member invite URL"
            onClick={(e) => (e.target as HTMLInputElement).select()}
            className="w-full rounded-[var(--radius-control)] border border-line bg-surface-sunken px-3.5 py-2.5 font-mono text-sm text-ink outline-none select-all focus:border-accent"
          />
        </div>

        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="primary"
            onClick={handleCopy}
            id="copy-member-link-btn"
            aria-label="Copy member invite link"
            className="shrink-0"
          >
            {copied ? (
              <>
                <svg
                  className="size-4"
                  viewBox="0 0 16 16"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <polyline points="3.5 8.5 6.5 11.5 12.5 4.5" />
                </svg>
                <span>Copied!</span>
              </>
            ) : (
              <>
                <svg
                  className="size-4"
                  viewBox="0 0 16 16"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.75"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <rect x="5.5" y="5.5" width="8" height="8" rx="1.5" />
                  <path d="M10.5 5.5V3.5a1.5 1.5 0 0 0-1.5-1.5h-5A1.5 1.5 0 0 0 2.5 3.5v5a1.5 1.5 0 0 0 1.5 1.5h2" />
                </svg>
                <span>Copy link</span>
              </>
            )}
          </Button>

          <a
            href={memberPath}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex h-10 items-center justify-center gap-1.5 rounded-[var(--radius-control)] border border-line px-3.5 text-sm font-medium text-ink-muted transition-colors hover:bg-surface-sunken hover:text-ink shrink-0"
            aria-label="Preview community page as a member in a new tab"
          >
            <span>Preview</span>
            <svg
              className="size-3.5"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M12 9v4a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h4" />
              <polyline points="10 2 14 2 14 6" />
              <line x1="7" y1="9" x2="14" y2="2" />
            </svg>
          </a>
        </div>
      </div>

      {!isConnected && (
        <p className="text-xs text-warning flex items-center gap-1.5">
          <span aria-hidden="true">⚠️</span>
          <span>
            Telegram group is not connected yet. Add the bot to your group so members can be invited
            after paying.
          </span>
        </p>
      )}

      {!isActive && (
        <p className="text-xs text-ink-muted flex items-center gap-1.5">
          <span aria-hidden="true">ℹ️</span>
          <span>
            This community is currently inactive. Activate it to allow members to view plans and join.
          </span>
        </p>
      )}
    </section>
  );
}
