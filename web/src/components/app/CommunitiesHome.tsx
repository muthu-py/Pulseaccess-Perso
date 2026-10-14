"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { CommunityList } from "@/components/communities/CommunityList";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { useCommunityCount, useCreatorTelegram } from "@/lib/creator";

/** Sends new creators to onboarding until Telegram is connected and a community exists. */
export function CommunitiesHome() {
  const router = useRouter();
  const telegram = useCreatorTelegram();
  const count = useCommunityCount();

  const ready = telegram.data !== undefined && count.data !== undefined;
  const needsOnboarding = ready && (!telegram.data.connected || count.data === 0);

  useEffect(() => {
    if (needsOnboarding) router.replace("/app/onboarding");
  }, [needsOnboarding, router]);

  if (telegram.error || count.error) {
    return <Alert tone="danger" title="Couldn't load your communities. Refresh to try again." />;
  }
  if (!ready || needsOnboarding) {
    return (
      <p className="flex items-center gap-2 text-ink-muted">
        <Spinner label="Loading" /> Loading…
      </p>
    );
  }

  return <CommunityList />;
}
