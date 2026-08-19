"use client";

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api, clearSession, getUser, setSession } from "@/lib/api";

type User = { id: string; email: string; full_name: string; role: string };

interface AuthContextValue {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, full_name: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<User | null>(() => getUser());
  const router = useRouter();

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
    <AuthContext.Provider value={{ user, login, register, logout }}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
