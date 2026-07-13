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

export async function uploadDocument(file: File): Promise<any> {
  loadTokens()
  const formData = new FormData()
  formData.append("file", file)
  const headers: Record<string, string> = {}
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`
  }
  const res = await fetch(`${API_BASE}/api/v1/rag/documents/upload`, {
    method: "POST",
    headers,
    body: formData,
  })
  if (!res.ok) {
    let detail = "Upload failed"
    try {
      const body = await res.json()
      detail = body.detail || body.message || JSON.stringify(body)
    } catch {}
    throw new ApiError(detail, res.status)
  }
  return res.json()
}

export async function listDocuments(params?: any): Promise<any> {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set("page", String(params.page))
  if (params?.page_size) searchParams.set("page_size", String(params.page_size))
  const qs = searchParams.toString()
  return apiRequest(`/api/v1/rag/documents${qs ? `?${qs}` : ""}`)
}

export async function searchDocuments(query: string, topK?: number): Promise<any> {
  const body: Record<string, unknown> = { query }
  if (topK) body.top_k = topK
  return apiRequest("/api/v1/rag/search", {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export async function deleteDocument(docId: string): Promise<any> {
  return apiRequest(`/api/v1/rag/documents/${docId}`, {
    method: "DELETE",
  })
}

export async function startTraining(config: any): Promise<any> {
  return apiRequest("/api/v1/training/start", {
    method: "POST",
    body: JSON.stringify(config),
  })
}

export async function listCheckpoints(): Promise<any> {
  return apiRequest("/api/v1/training/checkpoints")
}

export async function listModelVersions(modelName?: string): Promise<any> {
  const searchParams = new URLSearchParams()
  if (modelName) searchParams.set("model_name", modelName)
  const qs = searchParams.toString()
  return apiRequest(`/api/v1/models/versions${qs ? `?${qs}` : ""}`)
}

export async function getModelVersion(modelName: string, versionId: string): Promise<any> {
  return apiRequest(`/api/v1/models/${modelName}/versions/${versionId}`)
}

export async function rollbackVersion(modelName: string, versionId: string): Promise<any> {
  return apiRequest(`/api/v1/models/${modelName}/versions/${versionId}/rollback`, {
    method: "POST",
  })
}

export async function verifyVersion(modelName: string, versionId: string): Promise<any> {
  return apiRequest(`/api/v1/models/${modelName}/versions/${versionId}/verify`, {
    method: "POST",
  })
}

export async function getSystemHealth(): Promise<any> {
  return apiRequest("/api/v1/monitoring/health")
}

export async function getInferenceMetrics(): Promise<any> {
  return apiRequest("/api/v1/monitoring/inference")
}

export async function getControllerHealth(): Promise<any> {
  return apiRequest("/api/v1/monitoring/controller")
}

export async function getRegistryStats(): Promise<any> {
  return apiRequest("/api/v1/monitoring/registry")
}
