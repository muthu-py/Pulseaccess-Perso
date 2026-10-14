import type { Metadata } from "next";
import { Suspense, type ReactNode } from "react";

import { AppShell } from "@/components/app/AppShell";

export const metadata: Metadata = { robots: { index: false, follow: false } };

export default function AppLayout({ children }: { children: ReactNode }) {
  // usePathname() in the shell needs a Suspense boundary on dynamic routes like /app/communities/[id].
  return (
    <Suspense>
      <AppShell>{children}</AppShell>
    </Suspense>
  );
}
