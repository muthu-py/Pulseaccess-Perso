"use client";

import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { apiRequest, refreshCreatorSession, session } from "@/lib/api/client";

type AuthState = "loading" | "authenticated" | "anonymous";

type AuthContextValue = {
  state: AuthState;
  /** Store a fresh access token after OTP verification. */
  signIn: (accessToken: string) => void;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [state, setState] = useState<AuthState>("loading");

  // Restore the session on reload: the refresh cookie is the only thing that survives.
  useEffect(() => {
    let cancelled = false;
    refreshCreatorSession().then((token) => {
      if (!cancelled) setState(token ? "authenticated" : "anonymous");
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const signIn = useCallback((accessToken: string) => {
    session.set(accessToken, "creator");
    setState("authenticated");
  }, []);

  const signOut = useCallback(async () => {
    try {
      await apiRequest("/auth/logout", { method: "POST" });
    } catch {
      // Clear locally even if the server call fails; the cookie expires on its own.
    }
    session.clear("creator");
    queryClient.clear();
    setState("anonymous");
  }, [queryClient]);

  const value = useMemo(() => ({ state, signIn, signOut }), [state, signIn, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
