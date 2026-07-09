import { apiRequest } from "./client"
import type {
  Webhook, CreateWebhookRequest, UpdateWebhookRequest,
  WebhookEventLog, WebhookTestResult, TenantSettings,
} from "@/lib/types/webhooks"

export async function listWebhooks(): Promise<{ data: Webhook[] }> {
  return apiRequest("/api/v1/compliance/webhooks")
}

export async function getWebhook(webhookId: string): Promise<Webhook> {
  return apiRequest(`/api/v1/compliance/webhooks/${webhookId}`)
}

export async function createWebhook(data: CreateWebhookRequest): Promise<Webhook> {
  const params = new URLSearchParams()
  params.set("name", data.name)
  params.set("url", data.url)
  for (const event of data.events) {
    params.append("events", event)
  }
  if (data.retry_count !== undefined) params.set("retry_count", String(data.retry_count))
  if (data.timeout_ms !== undefined) params.set("timeout_ms", String(data.timeout_ms))
  return apiRequest(`/api/v1/compliance/webhooks?${params.toString()}`, {
    method: "POST",
  })
}

export async function updateWebhook(webhookId: string, data: UpdateWebhookRequest): Promise<Webhook> {
  const params = new URLSearchParams()
  if (data.name !== undefined) params.set("name", data.name)
  if (data.url !== undefined) params.set("url", data.url)
  if (data.events !== undefined) {
    for (const event of data.events) {
      params.append("events", event)
    }
  }
  if (data.is_active !== undefined) params.set("is_active", String(data.is_active))
  if (data.retry_count !== undefined) params.set("retry_count", String(data.retry_count))
  if (data.timeout_ms !== undefined) params.set("timeout_ms", String(data.timeout_ms))
  return apiRequest(`/api/v1/compliance/webhooks/${webhookId}?${params.toString()}`, {
    method: "PUT",
  })
}

export async function deleteWebhook(webhookId: string): Promise<void> {
  return apiRequest(`/api/v1/compliance/webhooks/${webhookId}`, {
    method: "DELETE",
  })
}

export async function testWebhook(webhookId: string): Promise<WebhookTestResult> {
  return apiRequest(`/api/v1/compliance/webhooks/${webhookId}/test`, {
    method: "POST",
  })
}

export async function getWebhookLogs(
  webhookId: string,
  params?: { page?: number; page_size?: number }
): Promise<{ data: WebhookEventLog[]; meta: { page: number; page_size: number; total: number } }> {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set("page", String(params.page))
  if (params?.page_size) searchParams.set("page_size", String(params.page_size))
  const qs = searchParams.toString()
  return apiRequest(`/api/v1/compliance/webhooks/${webhookId}/logs${qs ? `?${qs}` : ""}`)
}

export async function getSettings(): Promise<TenantSettings> {
  return apiRequest("/api/v1/compliance/settings")
}

export async function updateSettings(data: Partial<TenantSettings>): Promise<{ status: string; settings: TenantSettings }> {
  return apiRequest("/api/v1/compliance/settings", {
    method: "PUT",
    body: JSON.stringify(data),
  })
}
