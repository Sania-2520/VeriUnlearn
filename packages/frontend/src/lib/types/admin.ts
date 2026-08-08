export interface AdminUserUpdate {
  role?: string
  is_active?: boolean
}

export interface AnalyticsMetrics {
  metrics: Record<string, number>
  over_time: Array<{ date: string; value: number }>
}

export interface AdminJob {
  id: string
  type: string
  status: string
  created_at: string
}
