"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api, clearSession, getUser, setSession } from "@/lib/api";

type User = { id: string; email: string; full_name: string; role: string };

interface AuthContextValue {
  user: User | null;
  initialized: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, full_name: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  // NOTE: `user` intentionally starts as `null` on BOTH the server and the
  // first client render so SSR and CSR produce identical HTML. The persisted
  // session is read from localStorage only after mount (in useEffect), so the
  // initial paint is always the loading state and hydration can never diverge.
  const [user, setUserState] = useState<User | null>(null);
  const [initialized, setInitialized] = useState(false);
  const router = useRouter();

  useEffect(() => {
    setUserState(getUser());
    setInitialized(true);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await api.post<{ access_token: string; user: User }>("/api/v1/auth/login", {
        email,
        password,
      });
      setSession(res.access_token, res.user);
      setUserState(res.user);
      router.push("/assistant");
    },
    [router]
  );

  const register = useCallback(
    async (email: string, full_name: string, password: string) => {
      const res = await api.post<{ access_token: string; user: User }>("/api/v1/auth/register", {
        email,
        full_name,
        password,
      });
      setSession(res.access_token, res.user);
      setUserState(res.user);
      router.push("/assistant");
    },
    [router]
  );

  const logout = useCallback(() => {
    clearSession();
    setUserState(null);
    router.push("/login");
  }, [router]);

  return (
    <AuthContext.Provider value={{ user, initialized, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
