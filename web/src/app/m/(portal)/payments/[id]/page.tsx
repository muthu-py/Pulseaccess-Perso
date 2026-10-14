import type { Metadata } from "next";
import { Suspense } from "react";

import { PaymentStatus } from "@/components/member/PaymentStatus";

export const metadata: Metadata = { title: "Payment" };

export default function PaymentPage() {
  return (
    <Suspense>
      <PaymentStatus />
    </Suspense>
  );
}
