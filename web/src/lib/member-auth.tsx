"use client";

import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

import { session } from "@/lib/api/client";

type MemberAuthValue = {
  signedIn: boolean;
  signIn: (accessToken: string) => void;
  /** Also used when the backend answers 401: members have no refresh endpoint, so they log in again. */
  signOut: () => void;
};

const MemberAuthContext = createContext<MemberAuthValue | null>(null);

export function MemberAuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  // The token lives in memory only, so a full page load always starts signed out.
  const [signedIn, setSignedIn] = useState(() => session.get("member") !== null);

  const signIn = useCallback((accessToken: string) => {
    session.set(accessToken, "member");
    setSignedIn(true);
  }, []);

  const signOut = useCallback(() => {
    session.clear("member");
    queryClient.clear();
    setSignedIn(false);
  }, [queryClient]);

  const value = useMemo(() => ({ signedIn, signIn, signOut }), [signedIn, signIn, signOut]);
  return <MemberAuthContext.Provider value={value}>{children}</MemberAuthContext.Provider>;
}

export function useMemberAuth(): MemberAuthValue {
  const ctx = useContext(MemberAuthContext);
  if (!ctx) throw new Error("useMemberAuth must be used inside <MemberAuthProvider>");
  return ctx;
}
