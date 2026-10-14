import type { Metadata } from "next";
import { Suspense } from "react";

import { ConnectTelegram } from "@/components/member/ConnectTelegram";

export const metadata: Metadata = { title: "Connect Telegram" };

export default function ConnectTelegramPage() {
  return (
    <Suspense>
      <ConnectTelegram />
    </Suspense>
  );
}
