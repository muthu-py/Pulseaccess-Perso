import type { Metadata } from "next";

import { CommunitiesHome } from "@/components/app/CommunitiesHome";

export const metadata: Metadata = { title: "Communities" };

export default function CommunitiesPage() {
  return <CommunitiesHome />;
}
