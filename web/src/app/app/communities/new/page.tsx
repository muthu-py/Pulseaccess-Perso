import type { Metadata } from "next";

import { NewCommunity } from "@/components/communities/NewCommunity";

export const metadata: Metadata = { title: "New community" };

export default function NewCommunityPage() {
  return <NewCommunity />;
}
