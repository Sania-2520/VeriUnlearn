"use client"

import { useState, useCallback, useEffect } from "react"
import { motion } from "framer-motion"
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  ResponsiveContainer, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from "recharts"
import { toast } from "sonner"
import { clsx } from "clsx"
import { format, subDays } from "date-fns"
import { PageHeader } from "@/components/ui/page-header"
import { StatCard } from "@/components/ui/page-header"
import { Card, CardHeader, CardContent } from "@/components/ui/card"
import { Badge, statusTone } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import { loadLiveDashboard } from "@/lib/api/dashboard"
import {
  Activity, AlertTriangle, Archive,
  BarChart3, Bell, CheckCircle2, Clock, Cpu, Database,
  HardDrive, Layers, Loader2, MemoryStick,
  RefreshCw, Server, Shield, ShieldCheck, ShieldX,
  Trash2, TrendingUp, XCircle, Brain,
  X,
} from "lucide-react"

/* ─────────────────────────────────────────────
   Types
   ───────────────────────────────────────────── */

interface Metric {
  value: number
  trend: number
  unit?: string
}

interface SystemMetrics {
  activeModels: Metric
  activeDatasets: Metric
  runningJobs: Metric
  queueDepth: number[]
  gpuUtilization: number
  cpuLoad: number
  memoryUsage: number
  storageUsed: number
  storageTotal: number
}

interface ComplianceMetrics {
  trustScore: number
  privacyScore: number
  verificationRate: number
  pendingAudits: number
  activeCertificates: number
  trustTrend: { day: string; score: number }[]
}

interface UnlearningMetrics {
  requestsToday: number
  successfulDeletions: number
  failedRequests: number
  averageLatency: number
  requestsOverTime: { date: string; value: number }[]
  algorithmBreakdown: { name: string; value: number; color: string }[]
  algorithmComparison: { name: string; accuracy: number; speed: number; privacy: number }[]
}

interface ActivityEntry {
  id: string
  user: string
  action: string
  target: string
  timestamp: Date
  status: "completed" | "pending" | "failed" | "running"
}

interface ServiceHealth {
  name: string
  icon: typeof Server
  status: "healthy" | "degraded" | "down"
  latency: string
  uptime: string
}

interface AlertEntry {
  id: string
  severity: "critical" | "warning" | "info"
  title: string
  message: string
  timestamp: Date
}

/* ─────────────────────────────────────────────
   Mock data generators
   ───────────────────────────────────────────── */

function generateTimeSeries(days: number, min: number, max: number, smooth = true): { date: string; value: number }[] {
  const data: { date: string; value: number }[] = []
  let prev = (min + max) / 2
  for (let i = days; i >= 0; i--) {
    const noise = Math.random() * (max - min) * 0.4 - (max - min) * 0.2
    const change = smooth ? noise : Math.random() * (max - min) + min
    prev = Math.max(min, Math.min(max, prev + noise * 0.3))
    data.push({ date: format(subDays(new Date(), i), "MMM dd"), value: Math.round(prev) })
  }
  return data
}

function systemMetrics(): SystemMetrics {
  return {
    activeModels: { value: 24, trend: 12.5 },
    activeDatasets: { value: 156, trend: 8.3 },
    runningJobs: { value: 7, trend: -2.1 },
    queueDepth: Array.from({ length: 24 }, () => Math.floor(Math.random() * 40) + 5),
    gpuUtilization: 78,
    cpuLoad: 43,
    memoryUsage: 62,
    storageUsed: 3.4,
    storageTotal: 8,
  }
}

function complianceMetrics(): ComplianceMetrics {
  return {
    trustScore: 94,
    privacyScore: 88,
    verificationRate: 99.7,
    pendingAudits: 3,
    activeCertificates: 42,
    trustTrend: generateTimeSeries(14, 72, 96, true).map((d) => ({ day: d.date, score: d.value })),
  }
}

function unlearningMetrics(): UnlearningMetrics {
  return {
    requestsToday: 18,
    successfulDeletions: 16,
    failedRequests: 2,
    averageLatency: 347,
    requestsOverTime: generateTimeSeries(30, 5, 45, true),
    algorithmBreakdown: [
      { name: "SISA", value: 45, color: "var(--chart-1)" },
      { name: "Influence", value: 28, color: "var(--chart-2)" },
      { name: "Certified", value: 18, color: "var(--chart-3)" },
      { name: "Delta", value: 9, color: "var(--chart-4)" },
    ],
    algorithmComparison: [
      { name: "SISA", accuracy: 96, speed: 72, privacy: 88 },
      { name: "Influence", accuracy: 91, speed: 64, privacy: 82 },
      { name: "Certified", accuracy: 98, speed: 45, privacy: 97 },
      { name: "Delta", accuracy: 85, speed: 91, privacy: 74 },
    ],
  }
}

function recentActivity(): ActivityEntry[] {
  const actions: ActivityEntry["action"][] = [
    "Deletion request completed", "Audit log verified", "New model registered",
    "Certificate issued", "Privacy scan finished", "Webhook triggered",
    "MFA enabled", "Unlearning request submitted", "Proof generated",
    "Data access granted",
  ]
  const statuses: ActivityEntry["status"][] = ["completed", "running", "pending", "failed"]
  return Array.from({ length: 20 }, (_, i) => ({
    id: `act-${i}`,
    user: ["alice@corp.com", "bob@corp.com", "carol@corp.com", "dave@corp.com"][i % 4],
    action: actions[i % actions.length],
    target: `#${Math.random().toString(36).slice(2, 8).toUpperCase()}`,
    timestamp: new Date(Date.now() - i * 4500000),
    status: statuses[i % statuses.length] as ActivityEntry["status"],
  }))
}

function serviceHealth(): ServiceHealth[] {
  return [
    { name: "Backend API", icon: Server, status: "healthy", latency: "12ms", uptime: "99.99%" },
    { name: "ML Engine", icon: Cpu, status: "healthy", latency: "34ms", uptime: "99.95%" },
    { name: "PostgreSQL", icon: Database, status: "healthy", latency: "3ms", uptime: "99.99%" },
    { name: "Redis", icon: MemoryStick, status: "healthy", latency: "1ms", uptime: "100%" },
    { name: "Qdrant", icon: Layers, status: "degraded", latency: "89ms", uptime: "98.72%" },
    { name: "MinIO", icon: Archive, status: "healthy", latency: "7ms", uptime: "99.98%" },
    { name: "RabbitMQ", icon: Activity, status: "healthy", latency: "2ms", uptime: "100%" },
  ]
}

function systemAlerts(): AlertEntry[] {
  return [
    {
      id: "alert-1", severity: "critical",
      title: "Qdrant latency threshold exceeded",
      message: "Vector search latency spiked above 200ms on node-3. Auto-scaling triggered.",
      timestamp: new Date(Date.now() - 600000),
    },
    {
      id: "alert-2", severity: "warning",
      title: "Storage nearing capacity",
      message: "Model registry partition is at 82%. Consider archiving unused models.",
      timestamp: new Date(Date.now() - 1800000),
    },
    {
      id: "alert-3", severity: "warning",
      title: "Certificate expiring",
      message: "Client certificate 'prod-ml-01' expires in 7 days. Visit Certificate Manager.",
      timestamp: new Date(Date.now() - 3600000),
    },
    {
      id: "alert-4", severity: "info",
      title: "Weekly compliance report ready",
      message: "GDPR compliance summary for week 29 is generated and ready for review.",
      timestamp: new Date(Date.now() - 7200000),
    },
    {
      id: "alert-5", severity: "info",
      title: "System update scheduled",
      message: "v2.4.1 will be deployed on 2026-08-02 02:00 UTC. Expected downtime: 45s.",
      timestamp: new Date(Date.now() - 14400000),
    },
  ]
}

/* ─────────────────────────────────────────────
   Tooltip formatters
   ───────────────────────────────────────────── */

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="surface-elevated rounded-lg px-3 py-2 text-xs shadow-[var(--shadow-md)]">
      <p className="mb-1 font-medium text-[var(--text-primary)]">{label}</p>
      {payload.map((p: any, i: number) => (
        <p key={i} style={{ color: p.color }} className="tabular-nums">
          {p.name}: {p.value}
        </p>
      ))}
    </div>
  )
}

/* ─────────────────────────────────────────────
   Animation variants
   ───────────────────────────────────────────── */

const container = { hidden: {}, show: { transition: { staggerChildren: 0.04 } } }
const item = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.16, 1, 0.3, 1] } },
}

/* ─────────────────────────────────────────────
   Sparkline (mini inline chart)
   ───────────────────────────────────────────── */

function Sparkline({ data, color }: { data: number[]; color: string }) {
  const h = 32
  const w = 80
  const max = Math.max(...data, 1)
  const points = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - (v / max) * h}`).join(" ")
  return (
    <svg width={w} height={h} className="shrink-0" aria-hidden>
      <polyline fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" points={points} />
    </svg>
  )
}

/* ─────────────────────────────────────────────
   Gauge ring (for GPU utilization)
   ───────────────────────────────────────────── */

function GaugeRing({ value, size = 48 }: { value: number; size?: number }) {
  const stroke = 4
  const r = (size - stroke) / 2
  const circ = 2 * Math.PI * r
  const offset = circ * (1 - value / 100)
  const color = value > 80 ? "var(--danger)" : value > 60 ? "var(--warning)" : "var(--success)"
  return (
    <svg width={size} height={size} aria-hidden className="shrink-0">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--bg-subtle)" strokeWidth={stroke} />
      <circle
        cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color}
        strokeWidth={stroke} strokeLinecap="round"
        strokeDasharray={circ} strokeDashoffset={offset}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
        className="transition-all duration-700 ease-out"
      />
      <text x={size / 2} y={size / 2} textAnchor="middle" dominantBaseline="central"
        fill="var(--text-primary)" fontSize="11" fontWeight="700" fontFamily="var(--font-mono)">
        {value}%
      </text>
    </svg>
  )
}

/* ─────────────────────────────────────────────
   Helpers
   ───────────────────────────────────────────── */

const statusIcon = (s: ActivityEntry["status"]) =>
  ({ completed: CheckCircle2, running: Loader2, pending: Clock, failed: XCircle })[s]

const activityIcon = (action: string) =>
  action.includes("delet") || action.includes("unlearn") ? Trash2 :
  action.includes("audit") || action.includes("proof") ? ShieldCheck :
  action.includes("certif") ? Shield :
  action.includes("model") ? Brain :
  action.includes("privacy") ? ShieldX :
  action.includes("webhook") ? Activity : Bell

function timeAgo(d: Date) {
  const s = Math.floor((Date.now() - d.getTime()) / 1000)
  if (s < 60) return "just now"
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}

function alertIcon(s: AlertEntry["severity"]) {
  return s === "critical" ? AlertTriangle : s === "warning" ? AlertTriangle : Bell
}

/* ─────────────────────────────────────────────
   Status indicator dot
   ───────────────────────────────────────────── */

function StatusDot({ status }: { status: ServiceHealth["status"] }) {
  return (
    <span className={clsx("h-2 w-2 rounded-full shrink-0", {
      "bg-[var(--success)] shadow-[0_0_6px_var(--success)]": status === "healthy",
      "bg-[var(--warning)] shadow-[0_0_6px_var(--warning)]": status === "degraded",
      "bg-[var(--danger)] shadow-[0_0_6px_var(--danger)]": status === "down",
    })} />
  )
}

/* ─────────────────────────────────────────────
   Main Dashboard Component
   ───────────────────────────────────────────── */

export default function DashboardPage() {
  const [loading, setLoading] = useState(false)
  const [dataSource, setDataSource] = useState<"live" | "fallback">("fallback")
  const [metrics, setMetrics] = useState(systemMetrics)
  const [compliance] = useState(complianceMetrics)
  const [unlearning, setUnlearning] = useState(unlearningMetrics)
  const [activities] = useState(recentActivity)
  const [services] = useState(serviceHealth)
  const [alerts, setAlerts] = useState(systemAlerts)
  const [showAllActivities, setShowAllActivities] = useState(false)

  const refreshData = useCallback(async () => {
    setLoading(true)
    try {
      const snap = await loadLiveDashboard()
      setDataSource(snap.sources)
      if (snap.sources === "live") {
        setMetrics((prev) => ({
          ...prev,
          activeModels: {
            ...prev.activeModels,
            value: snap.modelCount ?? prev.activeModels.value,
          },
          runningJobs: {
            ...prev.runningJobs,
            value: snap.activeJobs ?? prev.runningJobs.value,
          },
        }))
        setUnlearning((prev) => ({
          ...prev,
          requestsToday: snap.runningUnlearningRequests ?? prev.requestsToday,
          successfulDeletions: snap.completedUnlearningRequests ?? prev.successfulDeletions,
        }))
      }
      toast.success(snap.sources === "live" ? "Dashboard synced with live data" : "Using cached sample data")
      setLoading(false)
    } catch {
      setDataSource("fallback")
      toast.error("Refresh failed")
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refreshData()
  }, [refreshData])

  const dismissAlert = useCallback((id: string) => {
    setAlerts((prev) => prev.filter((a) => a.id !== id))
    toast("Alert dismissed", { icon: <Bell className="h-4 w-4" /> })
  }, [])

  const visibleActivities = showAllActivities ? activities : activities.slice(0, 6)

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-72" />
          </div>
          <Skeleton className="h-9 w-28 rounded-lg" />
        </div>
        {[0, 1, 2].map((row) => (
          <div key={row} className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))" }}>
            {Array.from({ length: row === 0 ? 8 : 5 }).map((_, i) => (
              <div key={i} className="surface rounded-xl p-5">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="mt-3 h-7 w-14" />
                <Skeleton className="mt-2 h-3 w-20" />
              </div>
            ))}
          </div>
        ))}
        {[0, 1].map((row) => (
          <div key={`chart-${row}`} className="grid gap-4 md:grid-cols-2">
            {[0, 1].map((i) => (
              <div key={i} className="surface rounded-xl p-5">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="mt-4 h-48 w-full rounded-lg" />
              </div>
            ))}
          </div>
        ))}
      </div>
    )
  }

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="p-5 md:p-6 space-y-6 max-w-[1600px] mx-auto"
    >
      {/* ─────── Page Header ─────── */}
      <motion.div variants={item}>
        <PageHeader
          title="Executive Dashboard"
          description="Real-time overview of system health, compliance posture, and unlearning operations"
          actions={
            <div className="flex items-center gap-2">
              <Badge tone={dataSource === "live" ? "success" : "warning"} dot>
                {dataSource === "live" ? "Live data" : "Sample data"}
              </Badge>
              <button
                onClick={refreshData}
                className="inline-flex items-center gap-2 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-3.5 py-2 text-sm font-medium text-[var(--text-secondary)] transition-all hover:border-[var(--brand)] hover:text-[var(--brand-strong)] hover:bg-[var(--brand-soft)] cursor-pointer"
              >
                <RefreshCw className="h-4 w-4" />
                Refresh
              </button>
            </div>
          }
        />
      </motion.div>

      {/* ─────── Section: System Overview ─────── */}
      <motion.div variants={item}>
        <div className="mb-3 flex items-center gap-2">
          <Server className="h-4 w-4 text-[var(--text-tertiary)]" />
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">System Overview</h2>
        </div>
        <div className="grid gap-3 grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-8">
          <StatCard label="Active Models" value={metrics.activeModels.value} icon={Brain} tone="brand"
            delta={{ value: `${metrics.activeModels.trend}%`, positive: true }} hint="vs last week" />
          <StatCard label="Active Datasets" value={metrics.activeDatasets.value} icon={Database} tone="info"
            delta={{ value: `${metrics.activeDatasets.trend}%`, positive: true }} hint="vs last week" />
          <StatCard label="Running Jobs" value={metrics.runningJobs.value} icon={Loader2} tone="purple"
            delta={{ value: `${Math.abs(metrics.runningJobs.trend)}%`, positive: false }} hint="vs last week" />
          <div className="surface rounded-xl p-5 transition-shadow hover:shadow-[var(--shadow-md)]">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Queue Depth</p>
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent)]">
                <Layers className="h-4 w-4" />
              </span>
            </div>
            <p className="mt-3 text-2xl font-semibold tabular-nums text-[var(--text-primary)]">
              {metrics.queueDepth[metrics.queueDepth.length - 1]}
            </p>
            <div className="mt-2">
              <Sparkline data={metrics.queueDepth} color="var(--accent)" />
            </div>
          </div>
          <div className="surface rounded-xl p-5 transition-shadow hover:shadow-[var(--shadow-md)]">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">GPU Util</p>
              <span className="flex h-8 w-8 items-center justify-center rounded-lg"
                style={{ backgroundColor: "color-mix(in srgb, var(--chart-2) 14%, transparent)", color: "var(--chart-2)" }}>
                <Cpu className="h-4 w-4" />
              </span>
            </div>
            <div className="mt-2 flex items-center justify-between">
              <GaugeRing value={metrics.gpuUtilization} />
              <span className="text-[11px] text-[var(--text-tertiary)]">{metrics.gpuUtilization}%</span>
            </div>
          </div>
          <StatCard label="CPU Load" value={`${metrics.cpuLoad}%`} icon={BarChart3} tone="success"
            hint={metrics.cpuLoad < 50 ? "Low load" : "Moderate"} />
          <StatCard label="Memory" value={`${metrics.memoryUsage}%`} icon={MemoryStick} tone="warning"
            hint={`${Math.round(metrics.memoryUsage / 100 * 32)} / 32 GB`} />
          <div className="surface rounded-xl p-5 transition-shadow hover:shadow-[var(--shadow-md)]">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Storage</p>
              <span className="flex h-8 w-8 items-center justify-center rounded-lg"
                style={{ backgroundColor: "color-mix(in srgb, var(--chart-6) 14%, transparent)", color: "var(--chart-6)" }}>
                <HardDrive className="h-4 w-4" />
              </span>
            </div>
            <p className="mt-3 text-2xl font-semibold tabular-nums text-[var(--text-primary)]">
              {metrics.storageUsed}<span className="text-sm font-normal text-[var(--text-tertiary)]">TB</span>
            </p>
            <div className="mt-2 flex items-center gap-2">
              <Progress value={metrics.storageUsed / metrics.storageTotal * 100} size="sm" tone="brand" className="flex-1" />
              <span className="text-[11px] tabular-nums text-[var(--text-tertiary)]">
                {metrics.storageTotal} TB
              </span>
            </div>
          </div>
        </div>
      </motion.div>

      {/* ─────── Section: Compliance ─────── */}
      <motion.div variants={item}>
        <div className="mb-3 flex items-center gap-2">
          <Shield className="h-4 w-4 text-[var(--text-tertiary)]" />
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">Compliance Posture</h2>
        </div>
        <div className="grid gap-3 grid-cols-2 sm:grid-cols-3 md:grid-cols-5">
          <div className="surface rounded-xl p-5 transition-shadow hover:shadow-[var(--shadow-md)]">
            <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Trust Score</p>
            <div className="mt-2 flex items-end gap-3">
              <span className={clsx("text-3xl font-bold tabular-nums", {
                "text-[var(--success)]": compliance.trustScore >= 90,
                "text-[var(--warning)]": compliance.trustScore >= 70 && compliance.trustScore < 90,
                "text-[var(--danger)]": compliance.trustScore < 70,
              })}>{compliance.trustScore}</span>
              <span className="text-xs text-[var(--text-tertiary)] mb-1">/ 100</span>
            </div>
            <Progress value={compliance.trustScore} tone={compliance.trustScore >= 90 ? "success" : compliance.trustScore >= 70 ? "warning" : "danger"} className="mt-2" />
          </div>
          <div className="surface rounded-xl p-5 transition-shadow hover:shadow-[var(--shadow-md)]">
            <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Privacy Score</p>
            <div className="mt-2 flex items-end gap-3">
              <span className={clsx("text-3xl font-bold tabular-nums", {
                "text-[var(--success)]": compliance.privacyScore >= 85,
                "text-[var(--warning)]": compliance.privacyScore >= 65 && compliance.privacyScore < 85,
                "text-[var(--danger)]": compliance.privacyScore < 65,
              })}>{compliance.privacyScore}</span>
              <span className="text-xs text-[var(--text-tertiary)] mb-1">/ 100</span>
            </div>
            <Progress value={compliance.privacyScore} tone={compliance.privacyScore >= 85 ? "success" : "warning"} className="mt-2" />
          </div>
          <StatCard label="Verification Rate" value={`${compliance.verificationRate}%`} icon={CheckCircle2} tone="success" hint="Last 30 days" />
          <StatCard label="Pending Audits" value={compliance.pendingAudits} icon={ShieldX} tone="warning" hint="Requires attention" />
          <StatCard label="Active Certificates" value={compliance.activeCertificates} icon={ShieldCheck} tone="brand" hint="All valid" />
        </div>
      </motion.div>

      {/* ─────── Section: Machine Unlearning ─────── */}
      <motion.div variants={item}>
        <div className="mb-3 flex items-center gap-2">
          <Trash2 className="h-4 w-4 text-[var(--text-tertiary)]" />
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">Machine Unlearning</h2>
        </div>
        <div className="grid gap-3 grid-cols-2 sm:grid-cols-3 md:grid-cols-5">
          <StatCard label="Requests Today" value={unlearning.requestsToday} icon={Activity} tone="brand"
            delta={{ value: "18%", positive: true }} hint="vs yesterday" />
          <StatCard label="Successful" value={unlearning.successfulDeletions} icon={CheckCircle2} tone="success"
            hint="Completed" />
          <StatCard label="Failed" value={unlearning.failedRequests} icon={XCircle} tone="danger"
            hint="Needs review" />
          <StatCard label="Avg Latency" value={`${unlearning.averageLatency}`} icon={Clock} tone="info"
            hint="ms" />
          <div className="surface rounded-xl p-5 transition-shadow hover:shadow-[var(--shadow-md)]">
            <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Algorithms</p>
            <div className="mt-1 flex items-center justify-center h-[76px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={unlearning.algorithmBreakdown}
                    cx="50%" cy="50%"
                    innerRadius={20} outerRadius={34}
                    dataKey="value" stroke="none"
                  >
                    {unlearning.algorithmBreakdown.map((e) => (
                      <Cell key={e.name} fill={e.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-wrap gap-x-3 gap-y-0.5 justify-center">
              {unlearning.algorithmBreakdown.map((a) => (
                <span key={a.name} className="flex items-center gap-1 text-[10px] text-[var(--text-tertiary)]">
                  <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: a.color }} />
                  {a.name}
                </span>
              ))}
            </div>
          </div>
        </div>
      </motion.div>

      {/* ─────── Section: Interactive Charts ─────── */}
      <motion.div variants={item}>
        <div className="mb-3 flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-[var(--text-tertiary)]" />
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">Analytics</h2>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {/* Area Chart: Unlearning Requests */}
          <Card>
            <CardHeader
              title="Unlearning Requests (30d)"
              description="Daily deletion request volume"
              actions={<Badge tone="info" dot>Live</Badge>}
            />
            <CardContent>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={unlearning.requestsOverTime}>
                    <defs>
                      <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="var(--brand)" stopOpacity={0.25} />
                        <stop offset="100%" stopColor="var(--brand)" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 3" />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} width={36} />
                    <Tooltip content={<ChartTooltip />} />
                    <Area type="monotone" dataKey="value" stroke="var(--brand)" strokeWidth={2} fill="url(#areaGrad)" name="Requests" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Bar Chart: Algorithm Comparison */}
          <Card>
            <CardHeader
              title="Algorithm Comparison"
              description="Accuracy, speed & privacy by method"
              actions={<Badge tone="purple" dot>Benchmark</Badge>}
            />
            <CardContent>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={unlearning.algorithmComparison} barGap={2} barCategoryGap="20%">
                    <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 3" />
                    <XAxis dataKey="name" tick={{ fontSize: 11, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} width={36} domain={[0, 100]} />
                    <Tooltip content={<ChartTooltip />} />
                    <Legend wrapperStyle={{ fontSize: 11, color: "var(--text-secondary)" }} />
                    <Bar dataKey="accuracy" fill="var(--chart-1)" radius={[3, 3, 0, 0]} maxBarSize={24} name="Accuracy" />
                    <Bar dataKey="speed" fill="var(--chart-2)" radius={[3, 3, 0, 0]} maxBarSize={24} name="Speed" />
                    <Bar dataKey="privacy" fill="var(--chart-3)" radius={[3, 3, 0, 0]} maxBarSize={24} name="Privacy" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Line Chart: Trust Score Trend */}
          <Card>
            <CardHeader
              title="Trust Score Trend (14d)"
              description="Compliance trust score over time"
              actions={<Badge tone="success" dot>Stable</Badge>}
            />
            <CardContent>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={compliance.trustTrend}>
                    <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 3" />
                    <XAxis dataKey="day" tick={{ fontSize: 10, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                    <YAxis domain={[60, 100]} tick={{ fontSize: 11, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} width={36} />
                    <Tooltip content={<ChartTooltip />} />
                    <Line type="monotone" dataKey="score" stroke="var(--chart-6)" strokeWidth={2.5} dot={false} activeDot={{ r: 4, fill: "var(--chart-6)" }} name="Trust Score" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Pie Chart: Algorithm Usage */}
          <Card>
            <CardHeader
              title="Algorithm Usage Distribution"
              description="Breakdown by unlearning strategy"
              actions={<Badge tone="brand" dot>Active</Badge>}
            />
            <CardContent>
              <div className="h-64 flex items-center justify-center">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={unlearning.algorithmBreakdown}
                      cx="50%" cy="50%"
                      innerRadius={56} outerRadius={88}
                      paddingAngle={3}
                      dataKey="value"
                      stroke="none"
                    >
                      {unlearning.algorithmBreakdown.map((e) => (
                        <Cell key={e.name} fill={e.color}>
                          <label>
                            <text x="50%" y="50%" textAnchor="middle" dominantBaseline="central"
                              fill="var(--text-primary)" fontSize="14" fontWeight="700">
                              {e.value}%
                            </text>
                          </label>
                        </Cell>
                      ))}
                    </Pie>
                    <Tooltip content={<ChartTooltip />} />
                    <Legend
                      wrapperStyle={{ fontSize: 11, color: "var(--text-secondary)" }}
                      formatter={(value: string) => <span style={{ color: "var(--text-secondary)" }}>{value}</span>}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="flex flex-wrap justify-center gap-4 text-xs text-[var(--text-tertiary)]">
                {unlearning.algorithmBreakdown.map((a) => (
                  <span key={a.name} className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-sm" style={{ backgroundColor: a.color }} />
                    {a.name}: {a.value}%
                  </span>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </motion.div>

      {/* ─────── Bottom Row: Activity + Health + Alerts ─────── */}
      <motion.div variants={item} className="grid gap-4 xl:grid-cols-3">
        {/* Recent Activity Feed */}
        <Card className="xl:col-span-1">
          <CardHeader
            title="Recent Activity"
            description="Latest system events"
            actions={
              <button
                onClick={() => setShowAllActivities((p) => !p)}
                className="text-xs font-medium text-[var(--brand)] hover:underline cursor-pointer"
              >
                {showAllActivities ? "Show less" : "View all"}
              </button>
            }
          />
          <CardContent className="p-0">
            <div className="divide-y divide-[var(--border-subtle)] max-h-[380px] overflow-y-auto">
              {visibleActivities.map((a) => {
                const Icon = activityIcon(a.action)
                const StatusIcon = statusIcon(a.status)
                return (
                  <div key={a.id} className="flex items-start gap-3 px-5 py-3 hover:bg-[var(--bg-subtle)] transition-colors">
                    <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[var(--bg-subtle)] text-[var(--text-tertiary)]">
                      <Icon className="h-3.5 w-3.5" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-[var(--text-primary)] truncate">{a.action}</p>
                      <p className="text-xs text-[var(--text-tertiary)]">
                        {a.user} &middot; {a.target}
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-1 shrink-0">
                      <Badge tone={statusTone(a.status)} dot>{a.status}</Badge>
                      <span className="text-[10px] tabular-nums text-[var(--text-tertiary)]">{timeAgo(a.timestamp)}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>

        {/* System Health */}
        <Card className="xl:col-span-1">
          <CardHeader
            title="System Health"
            description="Service status & latency"
          />
          <CardContent className="p-0">
            <div className="divide-y divide-[var(--border-subtle)]">
              {services.map((s) => (
                <div key={s.name} className="flex items-center justify-between px-5 py-3.5 hover:bg-[var(--bg-subtle)] transition-colors">
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[var(--bg-subtle)] text-[var(--text-tertiary)]">
                      <s.icon className="h-3.5 w-3.5" />
                    </span>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-[var(--text-primary)]">{s.name}</p>
                      <div className="flex items-center gap-2 text-xs text-[var(--text-tertiary)]">
                        <span>{s.latency}</span>
                        <span>&middot;</span>
                        <span>{s.uptime} uptime</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={clsx("text-xs font-medium", {
                      "text-[var(--success)]": s.status === "healthy",
                      "text-[var(--warning)]": s.status === "degraded",
                      "text-[var(--danger)]": s.status === "down",
                    })}>{s.status}</span>
                    <StatusDot status={s.status} />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
          <div className="border-t border-[var(--border-subtle)] px-5 py-3 flex items-center justify-between text-xs text-[var(--text-tertiary)]">
            <span>5 / 7 services operational</span>
            <span className="flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--success)]" />
              All systems nominal
            </span>
          </div>
        </Card>

        {/* System Alerts */}
        <Card className="xl:col-span-1">
          <CardHeader
            title="System Alerts"
            description={`${alerts.length} active`}
            actions={
              alerts.length > 0 && (
                <button
                  onClick={() => { setAlerts([]); toast("All alerts dismissed") }}
                  className="text-xs font-medium text-[var(--text-tertiary)] hover:text-[var(--text-primary)] cursor-pointer"
                >
                  Dismiss all
                </button>
              )
            }
          />
          <CardContent className="p-0">
            {alerts.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 px-5 text-center">
                <CheckCircle2 className="h-10 w-10 text-[var(--success)] mb-3" />
                <p className="text-sm font-medium text-[var(--text-primary)]">All clear</p>
                <p className="text-xs text-[var(--text-tertiary)]">No active alerts</p>
              </div>
            ) : (
              <div className="max-h-[380px] overflow-y-auto">
                {alerts.map((a) => {
                  const AlertIcon = alertIcon(a.severity)
                  return (
                    <div
                      key={a.id}
                      className={clsx("relative flex gap-3 px-5 py-3.5 border-l-2 transition-colors hover:bg-[var(--bg-subtle)] group", {
                        "border-l-[var(--danger)]": a.severity === "critical",
                        "border-l-[var(--warning)]": a.severity === "warning",
                        "border-l-[var(--info)]": a.severity === "info",
                      })}
                    >
                      <span className={clsx("mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full", {
                        "bg-[var(--danger-soft)] text-[var(--danger)]": a.severity === "critical",
                        "bg-[var(--warning-soft)] text-[var(--warning)]": a.severity === "warning",
                        "bg-[var(--info-soft)] text-[var(--info)]": a.severity === "info",
                      })}>
                        <AlertIcon className="h-3 w-3" />
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-sm font-medium text-[var(--text-primary)]">{a.title}</p>
                          <button
                            onClick={() => dismissAlert(a.id)}
                            className="shrink-0 rounded p-0.5 text-[var(--text-tertiary)] opacity-0 group-hover:opacity-100 hover:text-[var(--text-primary)] transition-all cursor-pointer"
                            aria-label="Dismiss alert"
                          >
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </div>
                        <p className="text-xs text-[var(--text-secondary)] mt-0.5">{a.message}</p>
                        <p className="text-[10px] text-[var(--text-tertiary)] mt-1.5">{timeAgo(a.timestamp)}</p>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>

      {/* ─────── Footer timestamp ─────── */}
      <motion.div variants={item} className="flex items-center justify-between border-t border-[var(--border-subtle)] pt-4 text-[11px] text-[var(--text-tertiary)]">
        <span>Last updated: {format(new Date(), "MMM dd, yyyy HH:mm:ss")}</span>
        <span>VeriUnlearn v1.0 &middot; Executive Dashboard</span>
      </motion.div>
    </motion.div>
  )
}
