const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

class ApiError extends Error {
  status: number
  details: unknown

  constructor(message: string, status: number, details?: unknown) {
    super(message)
    this.status = status
    this.details = details
  }
}

async function refreshAccessToken(refreshToken: string): Promise<{ access_token: string; refresh_token: string } | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}

let accessToken: string | null = null
let refreshToken: string | null = null
let tokenRefreshPromise: Promise<boolean> | null = null

export function setTokens(access: string, refresh: string) {
  accessToken = access
  refreshToken = refresh
  if (typeof window !== "undefined") {
    localStorage.setItem("accessToken", access)
    localStorage.setItem("refreshToken", refresh)
  }
}

export function clearTokens() {
  accessToken = null
  refreshToken = null
  if (typeof window !== "undefined") {
    localStorage.removeItem("accessToken")
    localStorage.removeItem("refreshToken")
  }
}

export function loadTokens() {
  if (typeof window !== "undefined") {
    accessToken = localStorage.getItem("accessToken")
    refreshToken = localStorage.getItem("refreshToken")
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  loadTokens()

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  }

  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`
  }

  let res = await fetch(`${API_BASE}${path}`, { ...options, headers })

  if (res.status === 401 && refreshToken) {
    if (!tokenRefreshPromise) {
      tokenRefreshPromise = refreshAccessToken(refreshToken).then((tokens) => {
        tokenRefreshPromise = null
        if (tokens) {
          setTokens(tokens.access_token, tokens.refresh_token)
          return true
        }
        clearTokens()
        return false
      })
    }

    const refreshed = await tokenRefreshPromise
    if (refreshed) {
      headers["Authorization"] = `Bearer ${accessToken}`
      res = await fetch(`${API_BASE}${path}`, { ...options, headers })
    }
  }

  if (!res.ok) {
    let detail = "Request failed"
    try {
      const body = await res.json()
      detail = body.detail || body.message || JSON.stringify(body)
    } catch {}
    throw new ApiError(detail, res.status)
  }

  if (res.status === 204) return undefined as T
  return res.json()
}
