"use client";

import { useQuery } from "@tanstack/react-query";

import { apiRequest } from "@/lib/api/client";
import type { Member, MemberPlan, Payment, SubscriptionList, TelegramConnection } from "@/lib/api/types";

export const memberKeys = {
  me: ["member", "me"] as const,
  telegram: ["member", "telegram"] as const,
};

export function useMe() {
  return useQuery({
    queryKey: memberKeys.me,
    queryFn: () => apiRequest<Member>("/members/me", { auth: "member" }),
  });
}

/** Poll while waiting for the member to finish linking in Telegram. */
export function useMemberTelegram(opts: { poll?: boolean } = {}) {
  return useQuery({
    queryKey: memberKeys.telegram,
    queryFn: () => apiRequest<TelegramConnection>("/telegram/connect/member", { auth: "member" }),
    refetchInterval: (query) => (opts.poll && !query.state.data?.connected ? 3000 : false),
  });
}

export function useAvailablePlans(communityId: string) {
  return useQuery({
    queryKey: ["member", "plans", communityId],
    queryFn: () => apiRequest<MemberPlan[]>(`/communities/${communityId}/plans/available`, { auth: "member" }),
  });
}

/** Polls a payment until the backend says it is no longer open. */
export function usePayment(id: string) {
  return useQuery({
    queryKey: ["member", "payment", id],
    queryFn: () => apiRequest<Payment>(`/payments/${id}`, { auth: "member" }),
    refetchInterval: (query) => (query.state.data && query.state.data.status !== "created" ? false : 3000),
  });
}

export function useSubscriptions() {
  return useQuery({
    queryKey: ["member", "subscriptions"],
    queryFn: () => apiRequest<SubscriptionList>("/subscriptions/me", { auth: "member" }),
  });
}
