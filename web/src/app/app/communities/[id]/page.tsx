import type { Metadata } from "next";
import { Suspense } from "react";

import { CommunityDetail } from "@/components/communities/CommunityDetail";

export const metadata: Metadata = { title: "Community" };

export default function CommunityPage() {
  return (
    <Suspense>
      <CommunityDetail />
    </Suspense>
  );
}
