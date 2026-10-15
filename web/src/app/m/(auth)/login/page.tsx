import type { Metadata } from "next";
import { Suspense } from "react";

import { AuthCard } from "@/components/auth/AuthCard";
import { MemberLoginForm } from "@/components/member/MemberLoginForm";

export const metadata: Metadata = { title: "Member log in" };

export default function MemberLoginPage() {
  return (
    <AuthCard audience="member" title="Member log in" subtitle="We'll email you a one-time code.">
      <Suspense>
        <MemberLoginForm />
      </Suspense>
    </AuthCard>
  );
}
