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
