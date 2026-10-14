import type { Metadata } from "next";
import { Suspense } from "react";

import { AuthCard } from "@/components/auth/AuthCard";
import { MemberSignupForm } from "@/components/member/MemberSignupForm";

export const metadata: Metadata = { title: "Create a member account" };

export default function MemberSignupPage() {
  return (
    <AuthCard title="Create your account" subtitle="To join a paid Telegram community.">
      <Suspense>
        <MemberSignupForm />
      </Suspense>
    </AuthCard>
  );
}
