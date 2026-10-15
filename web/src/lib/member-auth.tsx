"use client";

import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { MEMBER_TOKEN_KEY, onMemberSessionExpired, session, tokenExpiry } from "@/lib/api/client";

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

  // A 401 on any member request means the token is gone: drop to signed-out so the shell redirects to login.
  useEffect(
    () =>
      onMemberSessionExpired(() => {
        queryClient.clear();
        setSignedIn(false);
      }),
    [queryClient],
  );

  // ── Client-side JWT expiry timer ──────────────────────────────────────────
  // Schedule a sign-out exactly when the current token expires so the member
  // gets redirected to login rather than hitting a 401 on the next request.
  useEffect(() => {
    if (!signedIn) return;

    const raw = localStorage.getItem(MEMBER_TOKEN_KEY) ?? session.get("member");
    if (!raw) return;

    const exp = tokenExpiry(raw);
    if (exp === null) return;

    const msUntilExpiry = exp - Date.now();
    if (msUntilExpiry <= 0) {
      // Already expired — sign out immediately
      session.clear("member");
      queryClient.clear();
      queueMicrotask(() => setSignedIn(false));
      return;
    }

    const id = window.setTimeout(() => {
      session.clear("member");
      queryClient.clear();
      setSignedIn(false);
    }, msUntilExpiry);

    return () => clearTimeout(id);
  }, [signedIn, queryClient]);

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
