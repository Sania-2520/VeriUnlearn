import { apiRequest } from "./client"
import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  MFAVerifyRequest,
  MFASetupResponse,
  ApiKey,
  ApiKeyCreated,
  CreateApiKeyRequest,
  Session,
  User,
  AuditEvent,
} from "@/lib/types/auth"

export async function login(data: LoginRequest): Promise<LoginResponse> {
  return apiRequest<LoginResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function register(data: RegisterRequest): Promise<RegisterResponse> {
  return apiRequest<RegisterResponse>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function logout(allSessions = false): Promise<void> {
  return apiRequest<void>("/api/v1/auth/logout", {
    method: "POST",
    body: JSON.stringify({ all_sessions: allSessions }),
  })
}

export async function refreshToken(token: string): Promise<LoginResponse> {
  return apiRequest<LoginResponse>("/api/v1/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: token }),
  })
}

export async function getMe(): Promise<User> {
  return apiRequest<User>("/api/v1/auth/me")
}

export async function updateProfile(data: Partial<{ full_name: string; avatar_url: string; preferences: Record<string, unknown> }>): Promise<User> {
  return apiRequest<User>("/api/v1/users/me", {
    method: "PATCH",
    body: JSON.stringify(data),
  })
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  return apiRequest<void>("/api/v1/auth/change-password", {
    method: "POST",
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  })
}

export async function forgotPassword(email: string): Promise<void> {
  return apiRequest<void>("/api/v1/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ email }),
  })
}

export async function resetPassword(token: string, newPassword: string): Promise<void> {
  return apiRequest<void>("/api/v1/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({ token, new_password: newPassword }),
  })
}

export async function setupMFA(password: string): Promise<MFASetupResponse> {
  return apiRequest<MFASetupResponse>("/api/v1/auth/mfa/totp/setup", {
    method: "POST",
    body: JSON.stringify({ password }),
  })
}

export async function enableMFA(secret: string, code: string): Promise<void> {
  return apiRequest<void>("/api/v1/auth/mfa/totp/enable", {
    method: "POST",
    body: JSON.stringify({ secret, code }),
  })
}

export async function disableMFA(code: string): Promise<void> {
  return apiRequest<void>("/api/v1/auth/mfa/totp/disable", {
    method: "POST",
    body: JSON.stringify({ code }),
  })
}

export async function verifyMFAChallenge(data: MFAVerifyRequest): Promise<LoginResponse> {
  return apiRequest<LoginResponse>("/api/v1/auth/mfa/verify", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function listApiKeys(): Promise<{ data: ApiKey[] }> {
  return apiRequest<{ data: ApiKey[] }>("/api/v1/auth/api-keys")
}

export async function createApiKey(data: CreateApiKeyRequest): Promise<ApiKeyCreated> {
  return apiRequest<ApiKeyCreated>("/api/v1/auth/api-keys", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function revokeApiKey(keyId: string): Promise<void> {
  return apiRequest<void>(`/api/v1/auth/api-keys/${keyId}`, {
    method: "DELETE",
  })
}

export async function listSessions(): Promise<{ data: Session[] }> {
  return apiRequest<{ data: Session[] }>("/api/v1/users/me/sessions")
}

export async function revokeSession(sessionId: string): Promise<void> {
  return apiRequest<void>(`/api/v1/users/me/sessions/${sessionId}`, {
    method: "DELETE",
  })
}

export async function revokeAllSessions(): Promise<void> {
  return apiRequest<void>("/api/v1/users/me/sessions", {
    method: "DELETE",
  })
}

export async function getAuditEvents(params?: { event_type?: string; page?: number; page_size?: number }): Promise<{ data: AuditEvent[]; meta: { page: number; page_size: number; total: number } }> {
  const searchParams = new URLSearchParams()
  if (params?.event_type) searchParams.set("event_type", params.event_type)
  if (params?.page) searchParams.set("page", String(params.page))
  if (params?.page_size) searchParams.set("page_size", String(params.page_size))
  const qs = searchParams.toString()
  return apiRequest(`/api/v1/audit/events${qs ? `?${qs}` : ""}`)
}

export async function getGoogleOAuthURL(): Promise<{ authorization_url: string }> {
  return apiRequest("/api/v1/auth/oauth/google/authorize")
}

export async function getGitHubOAuthURL(): Promise<{ authorization_url: string }> {
  return apiRequest("/api/v1/auth/oauth/github/authorize")
}
