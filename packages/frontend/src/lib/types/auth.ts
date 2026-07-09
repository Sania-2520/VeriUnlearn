export interface User {
  id: string
  tenant_id: string
  email: string
  full_name: string
  avatar_url: string | null
  role: string
  is_active: boolean
  is_email_verified: boolean
  mfa_enabled: boolean
  preferences: Record<string, unknown>
  created_at: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  challenge_token?: string
}

export interface RegisterRequest {
  email: string
  password: string
  full_name: string
  tenant_slug?: string
}

export interface RegisterResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: User
}

export interface MFAVerifyRequest {
  challenge_token: string
  code: string
}

export interface MFASetupResponse {
  secret: string
  provisioning_uri: string
}

export interface ApiKey {
  id: string
  name: string
  key_prefix: string
  scopes: string[]
  is_active: boolean
  created_at: string
  last_used_at: string | null
}

export interface ApiKeyCreated extends ApiKey {
  raw_key: string
}

export interface CreateApiKeyRequest {
  name: string
  scopes: string[]
}

export interface Session {
  id: string
  user_agent: string | null
  ip_address: string | null
  created_at: string
  expires_at: string
  is_current: boolean
}

export interface AuditEvent {
  id: string
  event_type: string
  event_version: string
  actor: { id: string | null; type: string }
  resource: { type: string | null; id: string | null }
  action: string
  status: string
  metadata: Record<string, unknown>
  changes: Record<string, unknown> | null
  ip_address: string | null
  session_id: string | null
  request_id: string | null
  event_hash: string
  previous_event_hash: string | null
  timestamp: string | null
}

export interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  challengeToken: string | null
}
