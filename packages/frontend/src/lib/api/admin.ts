import { apiRequest } from "./client"
import type { User } from "@/lib/types/auth"
import type { AdminUserUpdate, AnalyticsMetrics, AdminJob } from "@/lib/types/admin"

export async function listUsers(params?: {
  page?: number
  page_size?: number
  role?: string
  is_active?: boolean
}): Promise<{ data: User[]; meta: { page: number; page_size: number; total: number } }> {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set("page", String(params.page))
  if (params?.page_size) searchParams.set("page_size", String(params.page_size))
  if (params?.role) searchParams.set("role", params.role)
  if (params?.is_active !== undefined) searchParams.set("is_active", String(params.is_active))
  const qs = searchParams.toString()
  return apiRequest(`/api/v1/admin/users${qs ? `?${qs}` : ""}`)
}

export async function updateUser(userId: string, data: AdminUserUpdate): Promise<{ user: User }> {
  return apiRequest(`/api/v1/admin/users/${userId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
}

export async function getAnalytics(params?: {
  from?: string
  to?: string
  granularity?: string
}): Promise<AnalyticsMetrics> {
  const searchParams = new URLSearchParams()
  if (params?.from) searchParams.set("from", params.from)
  if (params?.to) searchParams.set("to", params.to)
  if (params?.granularity) searchParams.set("granularity", params.granularity)
  const qs = searchParams.toString()
  return apiRequest(`/api/v1/admin/analytics${qs ? `?${qs}` : ""}`)
}

export async function listJobs(params?: {
  page?: number
  page_size?: number
  status?: string
  type?: string
}): Promise<{ data: AdminJob[]; meta: { page: number; page_size: number; total: number } }> {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set("page", String(params.page))
  if (params?.page_size) searchParams.set("page_size", String(params.page_size))
  if (params?.status) searchParams.set("status", params.status)
  if (params?.type) searchParams.set("type", params.type)
  const qs = searchParams.toString()
  return apiRequest(`/api/v1/admin/jobs${qs ? `?${qs}` : ""}`)
}
