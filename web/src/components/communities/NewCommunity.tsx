"use client";

import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { apiRequest } from "@/lib/api/client";
import type { Community } from "@/lib/api/types";
import { creatorKeys } from "@/lib/creator";

import { CommunityForm } from "./CommunityForm";

export function NewCommunity() {
  const router = useRouter();
  const queryClient = useQueryClient();

  return (
    <div className="flex max-w-xl flex-col gap-6">
      <Link href="/app" className="text-sm text-accent underline underline-offset-4">
        Back to communities
      </Link>
      <h1 className="text-2xl font-semibold tracking-tight">New community</h1>
      <CommunityForm
        submitLabel="Create community"
        onSubmit={async (values) => {
          const created = await apiRequest<Community>("/communities", {
            method: "POST",
            body: { name: values.name, ...(values.description ? { description: values.description } : {}) },
          });
          await queryClient.invalidateQueries({ queryKey: creatorKeys.communities });
          router.replace(`/app/communities/${created.id}`);
        }}
      />
    </div>
  );
}
