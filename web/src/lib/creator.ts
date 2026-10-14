"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { apiRequest } from "@/lib/api/client";
import type { Community, CommunityList, TelegramConnection } from "@/lib/api/types";

export const creatorKeys = {
  telegram: ["creator", "telegram"] as const,
  communities: ["communities"] as const,
};

export const PAGE_SIZE = 10;

/** Whether the creator's Telegram account is linked. Poll while waiting for the link. */
export function useCreatorTelegram(opts: { poll?: boolean } = {}) {
  return useQuery({
    queryKey: creatorKeys.telegram,
    queryFn: () => apiRequest<TelegramConnection>("/telegram/connect/creator"),
    refetchInterval: (query) => (opts.poll && !query.state.data?.connected ? 3000 : false),
  });
}

/** Total communities across active and inactive, to know if onboarding is finished. */
export function useCommunityCount() {
  return useQuery({
    queryKey: [...creatorKeys.communities, "count"],
    queryFn: async () => {
      const [active, inactive] = await Promise.all([
        apiRequest<CommunityList>("/communities/active?page=1&page_size=1"),
        apiRequest<CommunityList>("/communities/inactive?page=1&page_size=1"),
      ]);
      return active.total + inactive.total;
    },
  });
}

export function useCommunities(tab: "active" | "inactive", page: number) {
  return useQuery({
    queryKey: [...creatorKeys.communities, "list", tab, page],
    queryFn: () => apiRequest<CommunityList>(`/communities/${tab}?page=${page}&page_size=${PAGE_SIZE}`),
    placeholderData: keepPreviousData,
  });
}

export function useCommunity(id: string) {
  return useQuery({
    queryKey: [...creatorKeys.communities, "detail", id],
    queryFn: () => apiRequest<Community>(`/communities/${id}`),
  });
}
