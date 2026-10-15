import type { components } from "./schema";

type Schemas = components["schemas"];

export type Creator = Schemas["CreatorResponse"];
export type RegisterRequest = Schemas["RegisterRequest"];
export type RequestOTPRequest = Schemas["RequestOTPRequest"];
export type VerifyOTPRequest = Schemas["VerifyOTPRequest"];
export type TokenResponse = Schemas["VerifyOTPResponse"];
export type TelegramConnection = Schemas["TelegramConnectionResponse"];
export type TelegramLink = Schemas["ConnectTelegramResponse"];
export type Community = Schemas["CommunityResponse"];
export type CommunityList = Schemas["CommunityListResponse"];
export type GroupConnection = Schemas["TelegramConnectionStatusResponse"];
export type Plan = Schemas["PlanResponse"];
export type Member = Schemas["MemberResponse"];
export type MemberPlan = Schemas["PlanResponse"];
export type Payment = Schemas["PaymentLinkResponse"] & { community_id?: string | null };
export type Subscription = Schemas["SubscriptionResponse"] & { community_id?: string | null };
export type SubscriptionList = Omit<Schemas["SubscriptionListResponse"], "subscriptions"> & {
  subscriptions: Subscription[];
};
export type InviteResponse = Schemas["InviteResponse"];

