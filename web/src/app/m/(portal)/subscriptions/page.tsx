import type { Metadata } from "next";

import { Subscriptions } from "@/components/member/Subscriptions";

export const metadata: Metadata = { title: "My subscriptions" };

export default function SubscriptionsPage() {
  return <Subscriptions />;
}
