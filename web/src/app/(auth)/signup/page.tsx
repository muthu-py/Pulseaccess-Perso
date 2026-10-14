import type { Metadata } from "next";

import { AuthCard } from "@/components/auth/AuthCard";
import { SignupForm } from "@/components/auth/SignupForm";

export const metadata: Metadata = { title: "Create your account" };

export default function SignupPage() {
  return (
    <AuthCard title="Create your account" subtitle="For creators running a paid Telegram community.">
      <SignupForm />
    </AuthCard>
  );
}
