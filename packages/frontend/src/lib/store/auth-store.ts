import { create } from "zustand"
import type { User, AuthState } from "@/lib/types/auth"
import { setTokens, clearTokens, loadTokens } from "@/lib/api/client"
import * as authApi from "@/lib/api/auth"

interface AuthActions {
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName: string) => Promise<void>
  logout: () => Promise<void>
  loadUser: () => Promise<void>
  setChallengeToken: (token: string | null) => void
  setUser: (user: User) => void
  updateUser: (partial: Partial<User>) => void
  clearAuth: () => void
  setAccessToken: (token: string) => void
  handleOAuthCallback: (code: string, provider: string) => Promise<boolean>
}

type AuthStore = AuthState & AuthActions

export const useAuthStore = create<AuthStore>((set, get) => ({
  user: null,
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
  isLoading: true,
  challengeToken: null,

  login: async (email: string, password: string) => {
    const res = await authApi.login({ email, password })
    if (res.challenge_token) {
      set({ challengeToken: res.challenge_token })
      return
    }
    setTokens(res.access_token, res.refresh_token)
    set({
      accessToken: res.access_token,
      refreshToken: res.refresh_token,
      isAuthenticated: true,
      challengeToken: null,
    })
    await get().loadUser()
  },

  register: async (email: string, password: string, fullName: string) => {
    const res = await authApi.register({ email, password, full_name: fullName })
    setTokens(res.access_token, res.refresh_token)
    set({
      accessToken: res.access_token,
      refreshToken: res.refresh_token,
      isAuthenticated: true,
      user: res.user,
    })
  },

  logout: async () => {
    try {
      await authApi.logout()
    } catch {}
    clearTokens()
    set({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      challengeToken: null,
    })
  },

  loadUser: async () => {
    loadTokens()
    const token = typeof window !== "undefined" ? localStorage.getItem("accessToken") : null
    if (!token) {
      set({ isLoading: false, isAuthenticated: false })
      return
    }
    try {
      const user = await authApi.getMe()
      set({
        user,
        isAuthenticated: true,
        isLoading: false,
        accessToken: token,
        refreshToken: localStorage.getItem("refreshToken"),
      })
    } catch {
      clearTokens()
      set({ isLoading: false, isAuthenticated: false })
    }
  },

  setChallengeToken: (token: string | null) => set({ challengeToken: token }),

  setUser: (user: User) => set({ user }),

  updateUser: (partial: Partial<User>) => {
    const current = get().user
    if (current) {
      set({ user: { ...current, ...partial } })
    }
  },

  clearAuth: () => {
    clearTokens()
    set({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      challengeToken: null,
    })
  },

  setAccessToken: (token: string) => set({ accessToken: token }),

  handleOAuthCallback: async (code: string, provider: string) => {
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/auth/oauth/${provider}/callback?code=${code}`,
      )
      if (!res.ok) return false
      const data = await res.json()
      if (data.challenge_token) {
        set({ challengeToken: data.challenge_token })
        return true
      }
      setTokens(data.access_token, data.refresh_token)
      set({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        isAuthenticated: true,
      })
      await get().loadUser()
      return true
    } catch {
      return false
    }
  },
}))
