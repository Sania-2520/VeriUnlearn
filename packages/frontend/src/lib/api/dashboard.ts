import { getSystemHealth, getRegistryStats } from "./client"
import { listRequests } from "./unlearning"
import { listJobs } from "./admin"

export interface LiveDashboardSnapshot {
  activeJobs: number | null
  runningUnlearningRequests: number | null
  completedUnlearningRequests: number | null
  modelCount: number | null
  backendHealthy: boolean | null
  sources: "live" | "fallback"
}

async function safeGet<T>(fn: () => Promise<T>): Promise<T | null> {
  try {
    return await fn()
  } catch {
    return null
  }
}

const base = (): LiveDashboardSnapshot => ({
  activeJobs: null,
  runningUnlearningRequests: null,
  completedUnlearningRequests: null,
  modelCount: null,
  backendHealthy: null,
  sources: "fallback",
})

export async function loadLiveDashboard(): Promise<LiveDashboardSnapshot> {
  const [health, jobs, registry, requests] = await Promise.all([
    safeGet(() => getSystemHealth()) as Promise<Record<string, unknown> | null>,
    safeGet(() => listJobs({ page: 1, page_size: 100 })) as Promise<{ data?: unknown[]; meta?: { total?: number } } | null>,
    safeGet(() => getRegistryStats()) as Promise<Record<string, unknown> | null>,
    safeGet(() => listRequests({ page: 1, page_size: 100 })) as Promise<{ data?: unknown[]; meta?: { total?: number } } | null>,
  ])

  if (!health && !jobs && !registry && !requests) return base()

  const snap = base()
  snap.sources = "live"
  snap.backendHealthy = health ? (health.backend as string) === "healthy" : null

  if (jobs?.data) {
    snap.activeJobs = (jobs.data as { status?: string }[]).filter((j) => j.status === "running").length
    snap.modelCount = jobs.meta?.total ?? jobs.data.length
  }

  if (requests?.data) {
    const items = requests.data as { status?: string }[]
    snap.runningUnlearningRequests = items.filter(
      (r) => r.status === "pending" || r.status === "running",
    ).length
    snap.completedUnlearningRequests = items.filter(
      (r) => r.status === "completed" || r.status === "success",
    ).length
  }

  return snap
}