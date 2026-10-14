import type { Metadata } from "next";
import { Suspense } from "react";

import { AuthCard } from "@/components/auth/AuthCard";
import { LoginForm } from "@/components/auth/LoginForm";

export const metadata: Metadata = { title: "Log in" };

export default function LoginPage() {
  return (
    <AuthCard title="Log in to PulseAccess" subtitle="We'll email you a one-time code.">
      <Suspense>
        <LoginForm />
      </Suspense>
    </AuthCard>
  );
}
