export interface Webhook {
  id: string
  name: string
  url: string
  events: string[]
  status: "active" | "failing" | "disabled"
  is_active: boolean
  headers: Record<string, string> | null
  retry_count: number
  timeout_ms: number
  last_success_at: string | null
  last_failure_at: string | null
  consecutive_failures: number
  created_at: string
  updated_at: string
}

export interface CreateWebhookRequest {
  name: string
  url: string
  events: string[]
  retry_count?: number
  timeout_ms?: number
}

export interface UpdateWebhookRequest {
  name?: string
  url?: string
  events?: string[]
  is_active?: boolean
  retry_count?: number
  timeout_ms?: number
}

export interface WebhookEventLog {
  id: string
  webhook_id: string
  event_type: string
  payload: Record<string, unknown>
  status: "pending" | "delivered" | "failed" | "retrying"
  response_code: number | null
  response_body: string | null
  attempt_count: number
  max_attempts: number
  next_retry_at: string | null
  created_at: string
  completed_at: string | null
}

export interface TenantSettings {
  timezone: string
  date_format: string
  notification_email: string | null
  gdpr_contact_email: string | null
  data_retention_days: number
  max_failed_login_attempts: number
  session_timeout_minutes: number
  mfa_enforced: boolean
  audit_retention_days: number
  webhook_retry_max_attempts: number
  webhook_retry_delay_seconds: number
  webhook_timeout_ms: number
  allowed_ip_ranges: string[]
  custom_branding: Record<string, unknown>
}

export interface WebhookTestResult {
  success: boolean
  status_code: number | null
  response: string | null
  duration_ms: number | null
  error: string | null
}
