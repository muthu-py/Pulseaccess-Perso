import { Suspense, type ReactNode } from "react";

import { MemberShell } from "@/components/member/MemberShell";

export default function PortalLayout({ children }: { children: ReactNode }) {
  // usePathname() in the shell needs a Suspense boundary on dynamic routes.
  return (
    <Suspense>
      <MemberShell>{children}</MemberShell>
    </Suspense>
  );
}
