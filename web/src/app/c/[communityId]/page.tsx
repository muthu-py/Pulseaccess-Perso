import type { Metadata } from "next";
import { Suspense } from "react";

import { CommunityPlans } from "@/components/member/CommunityPlans";

export const metadata: Metadata = { title: "Choose a plan" };

export default function CommunityPlansPage() {
  return (
    <Suspense>
      <CommunityPlans />
    </Suspense>
  );
}
