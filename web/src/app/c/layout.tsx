import type { Metadata } from "next";
import { Suspense, type ReactNode } from "react";

import { MemberShell } from "@/components/member/MemberShell";

export const metadata: Metadata = { robots: { index: false, follow: false } };

// Community plan pages need a member login for now, so they share the member shell.
export default function CommunityLayout({ children }: { children: ReactNode }) {
  return (
    <Suspense>
      <MemberShell>{children}</MemberShell>
    </Suspense>
  );
}
