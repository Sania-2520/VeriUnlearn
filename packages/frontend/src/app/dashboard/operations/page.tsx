"use client"

import { useState, useEffect, useRef, useCallback, useMemo } from "react"
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line,
} from "recharts"
import { motion, AnimatePresence } from "framer-motion"
import { toast } from "sonner"
import { clsx } from "clsx"
import {
  Activity, Clock, Bell, BellOff, ChevronDown, ChevronRight, Search,
  CheckCircle2, AlertTriangle, AlertCircle, Info, XCircle, Copy,
  Server, Cpu, HardDrive, Globe, Database,
  Layers, Boxes, Workflow, Zap, Wifi, ScrollText,
  ShieldCheck, ArrowUp, ArrowDown,
  ToggleLeft, ToggleRight, Plus, ExternalLink,
} from "lucide-react"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Badge, statusTone } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table"
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select"

/* ──────────────────────────────────────────────
   Types
   ────────────────────────────────────────────── */

type TimeRange = "1h" | "6h" | "24h" | "7d" | "30d" | "custom"
type RefreshInterval = 10 | 30 | 60 | 300
type EventSeverity = "success" | "warning" | "error" | "info"
type LogLevel = "ERROR" | "WARN" | "INFO" | "DEBUG"
type AlertSeverity = "critical" | "warning" | "info"
type TabId = "active" | "history" | "configure"

interface MetricPoint {
  time: string
  value: number
}

interface ServiceHealth {
  name: string
  icon: string
  status: "healthy" | "degraded" | "down"
  lastCheck: string
  responseTime: number
  uptime24h: number
  requests24h: number
  errors24h: number
  sparkline: MetricPoint[]
}

interface ActivityEvent {
  id: string
  timestamp: string
  type: EventSeverity
  description: string
  source: string
  status: string
}

interface Alert {
  id: string
  severity: AlertSeverity
  title: string
  description: string
  timestamp: string
  service: string
  acknowledged: boolean
  acknowledgedBy?: string
  resolvedAt?: string
  duration?: string
}

interface AlertRule {
  id: string
  name: string
  metric: string
  condition: string
  threshold: number
  enabled: boolean
}

interface InfraNode {
  id: string
  name: string
  status: "healthy" | "degraded" | "down"
  x: number
  y: number
  connections: string[]
}

interface LogEntry {
  id: string
  timestamp: string
  level: LogLevel
  service: string
  message: string
}

/* ──────────────────────────────────────────────
   Mock Data Generators
   ────────────────────────────────────────────── */

function generateSparkline(points = 24, base = 50, variance = 20): MetricPoint[] {
  return Array.from({ length: points }, (_, i) => ({
    time: `${i}h`,
    value: Math.max(0, base + Math.random() * variance * 2 - variance),
  }))
}

const servicesData: ServiceHealth[] = [
  { name: "API Gateway", icon: "Globe", status: "healthy", lastCheck: "2s ago", responseTime: 12, uptime24h: 99.98, requests24h: 142830, errors24h: 23, sparkline: generateSparkline(24, 45, 15) },
  { name: "ML Engine", icon: "Cpu", status: "healthy", lastCheck: "1s ago", responseTime: 48, uptime24h: 99.95, requests24h: 89120, errors24h: 12, sparkline: generateSparkline(24, 60, 25) },
  { name: "Verification Service", icon: "ShieldCheck", status: "healthy", lastCheck: "3s ago", responseTime: 156, uptime24h: 99.99, requests24h: 34560, errors24h: 5, sparkline: generateSparkline(24, 30, 10) },
  { name: "Certificate Service", icon: "ScrollText", status: "degraded", lastCheck: "5s ago", responseTime: 234, uptime24h: 98.72, requests24h: 12450, errors24h: 89, sparkline: generateSparkline(24, 70, 30) },
  { name: "Database (PostgreSQL)", icon: "Database", status: "healthy", lastCheck: "0s ago", responseTime: 8, uptime24h: 100, requests24h: 567890, errors24h: 2, sparkline: generateSparkline(24, 20, 8) },
  { name: "Cache (Redis)", icon: "Layers", status: "healthy", lastCheck: "1s ago", responseTime: 2, uptime24h: 100, requests24h: 890123, errors24h: 0, sparkline: generateSparkline(24, 10, 5) },
  { name: "Vector Store (Qdrant)", icon: "Boxes", status: "healthy", lastCheck: "2s ago", responseTime: 18, uptime24h: 99.97, requests24h: 67890, errors24h: 8, sparkline: generateSparkline(24, 35, 12) },
  { name: "Object Storage (MinIO)", icon: "HardDrive", status: "healthy", lastCheck: "4s ago", responseTime: 45, uptime24h: 99.93, requests24h: 234560, errors24h: 15, sparkline: generateSparkline(24, 40, 18) },
  { name: "Message Queue (RabbitMQ)", icon: "Workflow", status: "degraded", lastCheck: "3s ago", responseTime: 67, uptime24h: 99.45, requests24h: 456780, errors24h: 45, sparkline: generateSparkline(24, 50, 22) },
  { name: "WebSocket Server", icon: "Wifi", status: "healthy", lastCheck: "2s ago", responseTime: 5, uptime24h: 99.89, requests24h: 123450, errors24h: 7, sparkline: generateSparkline(24, 25, 10) },
]

const activityEvents: ActivityEvent[] = [
  { id: "1", timestamp: "2026-07-27T14:32:00Z", type: "success", description: "Unlearning job VU-2841 completed", source: "ML Engine", status: "Completed" },
  { id: "2", timestamp: "2026-07-27T14:30:15Z", type: "error", description: "Database connection pool exhausted", source: "API Gateway", status: "Error" },
  { id: "3", timestamp: "2026-07-27T14:28:45Z", type: "warning", description: "Certificate expiring in 7 days", source: "Certificate Service", status: "Warning" },
  { id: "4", timestamp: "2026-07-27T14:25:30Z", type: "info", description: "New model version v2.4.1 deployed", source: "ML Engine", status: "Info" },
  { id: "5", timestamp: "2026-07-27T14:22:10Z", type: "success", description: "Verification proof generated for job VU-2839", source: "Verification Service", status: "Completed" },
  { id: "6", timestamp: "2026-07-27T14:20:00Z", type: "error", description: "Message queue consumer timeout", source: "Message Queue", status: "Error" },
  { id: "7", timestamp: "2026-07-27T14:18:30Z", type: "warning", description: "Redis memory usage at 78%", source: "Cache (Redis)", status: "Warning" },
  { id: "8", timestamp: "2026-07-27T14:15:45Z", type: "info", description: "Qdrant collection index rebuilt", source: "Vector Store", status: "Info" },
  { id: "9", timestamp: "2026-07-27T14:12:20Z", type: "success", description: "Certificate issued for deployment v2.4", source: "Certificate Service", status: "Completed" },
  { id: "10", timestamp: "2026-07-27T14:10:00Z", type: "info", description: "System backup completed (1.2 GB)", source: "Object Storage", status: "Info" },
  { id: "11", timestamp: "2026-07-27T14:08:15Z", type: "success", description: "WebSocket connection restored (node-5)", source: "WebSocket Server", status: "Completed" },
  { id: "12", timestamp: "2026-07-27T14:05:30Z", type: "warning", description: "API rate limit approaching threshold", source: "API Gateway", status: "Warning" },
  { id: "13", timestamp: "2026-07-27T14:02:45Z", type: "info", description: "New adapter registered: Azure Blob", source: "Object Storage", status: "Info" },
  { id: "14", timestamp: "2026-07-27T14:00:00Z", type: "success", description: "All services healthy after rolling update", source: "API Gateway", status: "Completed" },
  { id: "15", timestamp: "2026-07-27T13:55:20Z", type: "error", description: "ML Engine inference timeout on model v2.3", source: "ML Engine", status: "Error" },
]

const activeAlerts: Alert[] = [
  { id: "A-001", severity: "critical", title: "Database connection pool > 90%", description: "PostgreSQL connection pool has exceeded 90% utilization for 5+ minutes", timestamp: "2026-07-27T14:28:00Z", service: "Database (PostgreSQL)", acknowledged: false },
  { id: "A-002", severity: "critical", title: "Certificate Service latency spike", description: "P99 latency > 500ms sustained for 3 minutes", timestamp: "2026-07-27T14:22:00Z", service: "Certificate Service", acknowledged: false },
  { id: "A-003", severity: "warning", title: "Redis memory usage > 75%", description: "Cache eviction rate increasing, memory at 78%", timestamp: "2026-07-27T14:18:00Z", service: "Cache (Redis)", acknowledged: true, acknowledgedBy: "Alice Chen" },
  { id: "A-004", severity: "warning", title: "Message queue consumer lag", description: "Consumer lag > 1000 messages on queue 'verification'", timestamp: "2026-07-27T14:10:00Z", service: "Message Queue (RabbitMQ)", acknowledged: false },
  { id: "A-005", severity: "info", title: "API rate limit at 70%", description: "API Gateway approaching rate limit for tier-2 clients", timestamp: "2026-07-27T14:05:00Z", service: "API Gateway", acknowledged: false },
  { id: "A-006", severity: "info", title: "Certificate expiry in 7 days", description: "TLS certificate for *.veriunlearn.io expires Aug 3", timestamp: "2026-07-27T14:00:00Z", service: "Certificate Service", acknowledged: true, acknowledgedBy: "Bob Singh" },
]

const resolvedAlerts: Alert[] = [
  { id: "R-001", severity: "critical", title: "MinIO disk space critical", description: "Disk usage at 94% on object storage node", timestamp: "2026-07-26T09:00:00Z", service: "Object Storage (MinIO)", acknowledged: true, acknowledgedBy: "Carol Davis", resolvedAt: "2026-07-26T09:45:00Z", duration: "45m" },
  { id: "R-002", severity: "warning", title: "ML Engine GPU temperature high", description: "GPU 0 temperature exceeded 85°C", timestamp: "2026-07-26T07:30:00Z", service: "ML Engine", acknowledged: true, acknowledgedBy: "Alice Chen", resolvedAt: "2026-07-26T08:15:00Z", duration: "45m" },
  { id: "R-003", severity: "critical", title: "Qdrant search latency spike", description: "P95 search latency > 2s for ANN queries", timestamp: "2026-07-25T22:00:00Z", service: "Vector Store (Qdrant)", acknowledged: true, acknowledgedBy: "Bob Singh", resolvedAt: "2026-07-25T23:30:00Z", duration: "1h 30m" },
  { id: "R-004", severity: "info", title: "WebSocket reconnect rate high", description: "Reconnect rate > 5/min on WebSocket server", timestamp: "2026-07-25T16:00:00Z", service: "WebSocket Server", acknowledged: true, acknowledgedBy: "Carol Davis", resolvedAt: "2026-07-25T16:30:00Z", duration: "30m" },
  { id: "R-005", severity: "warning", title: "Verification queue backlog", description: "Unprocessed verification requests > 500", timestamp: "2026-07-25T14:00:00Z", service: "Verification Service", acknowledged: true, acknowledgedBy: "Alice Chen", resolvedAt: "2026-07-25T15:45:00Z", duration: "1h 45m" },
]

const alertRules: AlertRule[] = [
  { id: "R1", name: "High CPU Usage", metric: "cpu_usage", condition: ">", threshold: 80, enabled: true },
  { id: "R2", name: "Memory Pressure", metric: "memory_usage", condition: ">", threshold: 85, enabled: true },
  { id: "R3", name: "Error Rate Spike", metric: "error_rate", condition: ">", threshold: 5, enabled: true },
  { id: "R4", name: "High Latency", metric: "p99_latency", condition: ">", threshold: 500, enabled: false },
  { id: "R5", name: "Queue Depth Warning", metric: "queue_depth", condition: ">", threshold: 1000, enabled: true },
  { id: "R6", name: "Certificate Expiry", metric: "days_until_expiry", condition: "<", threshold: 14, enabled: false },
]

const infraNodes: InfraNode[] = [
  { id: "gw", name: "API Gateway", status: "healthy", x: 50, y: 10, connections: ["ml", "verify", "ws"] },
  { id: "ml", name: "ML Engine", status: "healthy", x: 20, y: 35, connections: ["db", "cache", "vector"] },
  { id: "verify", name: "Verification", status: "healthy", x: 50, y: 35, connections: ["db", "cert", "queue"] },
  { id: "cert", name: "Certificate", status: "degraded", x: 80, y: 35, connections: ["db"] },
  { id: "db", name: "PostgreSQL", status: "healthy", x: 20, y: 60, connections: ["storage"] },
  { id: "cache", name: "Redis", status: "healthy", x: 40, y: 60, connections: [] },
  { id: "vector", name: "Qdrant", status: "healthy", x: 60, y: 60, connections: ["storage"] },
  { id: "storage", name: "MinIO", status: "healthy", x: 40, y: 85, connections: [] },
  { id: "queue", name: "RabbitMQ", status: "degraded", x: 60, y: 85, connections: ["storage"] },
  { id: "ws", name: "WebSocket", status: "healthy", x: 80, y: 10, connections: ["verify"] },
]

const logEntries: LogEntry[] = [
  { id: "L1", timestamp: "14:32:01", level: "INFO", service: "API Gateway", message: "Request completed GET /api/v1/health in 12ms" },
  { id: "L2", timestamp: "14:31:58", level: "WARN", service: "Certificate Service", message: "Certificate veriunlearn.io expires in 7 days" },
  { id: "L3", timestamp: "14:31:55", level: "ERROR", service: "API Gateway", message: "Connection pool exhausted: 48/50 connections in use" },
  { id: "L4", timestamp: "14:31:52", level: "INFO", service: "ML Engine", message: "Inference completed for job VU-2841 (latency: 156ms)" },
  { id: "L5", timestamp: "14:31:48", level: "DEBUG", service: "Message Queue", message: "Consumer ack received for message msg_89342" },
  { id: "L6", timestamp: "14:31:45", level: "ERROR", service: "Message Queue", message: "Consumer timeout on queue 'verification' after 30s" },
  { id: "L7", timestamp: "14:31:42", level: "INFO", service: "Database", message: "Query completed: SELECT avg(latency) FROM metrics (2.3ms)" },
  { id: "L8", timestamp: "14:31:38", level: "WARN", service: "Cache (Redis)", message: "Memory usage: 78% (evictions: 12/min)" },
  { id: "L9", timestamp: "14:31:35", level: "INFO", service: "WebSocket Server", message: "Client connected: node-5 (session ws_7721)" },
  { id: "L10", timestamp: "14:31:30", level: "INFO", service: "Object Storage", message: "Backup completed: 1.2 GB in 4.3s" },
  { id: "L11", timestamp: "14:31:25", level: "DEBUG", service: "ML Engine", message: "GPU 0: 62°C, utilization 45%, memory 8.2/24 GB" },
  { id: "L12", timestamp: "14:31:20", level: "ERROR", service: "ML Engine", message: "Inference timeout on model v2.3 after 30s" },
  { id: "L13", timestamp: "14:31:15", level: "WARN", service: "API Gateway", message: "Rate limit at 70% for tier-2 client api_key_84" },
  { id: "L14", timestamp: "14:31:10", level: "INFO", service: "Verification Service", message: "Proof generated for job VU-2839 in 2.1s" },
  { id: "L15", timestamp: "14:31:05", level: "INFO", service: "Vector Store", message: "Collection 'models_v2' index rebuilt (12ms)" },
  { id: "L16", timestamp: "14:31:00", level: "INFO", service: "API Gateway", message: "All services healthy after rolling update" },
  { id: "L17", timestamp: "14:30:55", level: "ERROR", service: "Certificate Service", message: "OCSP responder unreachable, using cached status" },
  { id: "L18", timestamp: "14:30:50", level: "INFO", service: "Certificate Service", message: "Certificate issued for deployment v2.4" },
  { id: "L19", timestamp: "14:30:45", level: "DEBUG", service: "Database", message: "Connection pool: 32/50 connections in use" },
  { id: "L20", timestamp: "14:30:40", level: "INFO", service: "Message Queue", message: "Queue 'unlearning' depth: 234 messages" },
]

const resourceChartData = Array.from({ length: 24 }, (_, i) => ({
  time: `${i}:00`,
  "API Gateway": 35 + Math.random() * 30,
  "ML Engine": 65 + Math.random() * 30,
  "Database": 25 + Math.random() * 20,
  "Redis": 15 + Math.random() * 15,
  "RabbitMQ": 30 + Math.random() * 25,
}))

const networkData = Array.from({ length: 24 }, (_, i) => ({
  time: `${i}:00`,
  inbound: 200 + Math.random() * 400,
  outbound: 150 + Math.random() * 350,
}))

const diskData = Array.from({ length: 24 }, (_, i) => ({
  time: `${i}:00`,
  read: 40 + Math.random() * 80,
  write: 25 + Math.random() * 60,
}))

/* ──────────────────────────────────────────────
   Helpers
   ────────────────────────────────────────────── */

const serviceIconMap: Record<string, React.ReactNode> = {
  Globe: <Globe className="h-4 w-4" />,
  Cpu: <Cpu className="h-4 w-4" />,
  ShieldCheck: <ShieldCheck className="h-4 w-4" />,
  ScrollText: <ScrollText className="h-4 w-4" />,
  Database: <Database className="h-4 w-4" />,
  Layers: <Layers className="h-4 w-4" />,
  Boxes: <Boxes className="h-4 w-4" />,
  HardDrive: <HardDrive className="h-4 w-4" />,
  Workflow: <Workflow className="h-4 w-4" />,
  Wifi: <Wifi className="h-4 w-4" />,
}

function statusColor(status: string) {
  if (status === "healthy") return "var(--success)"
  if (status === "degraded") return "var(--warning)"
  return "var(--danger)"
}

function formatNumber(n: number) {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M"
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K"
  return n.toString()
}

function formatTime(iso: string) {
  const d = new Date(iso)
  return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })
}

const logLevelBadge: Record<LogLevel, { tone: "danger" | "warning" | "info" | "neutral"; label: string }> = {
  ERROR: { tone: "danger", label: "ERROR" },
  WARN: { tone: "warning", label: "WARN" },
  INFO: { tone: "info", label: "INFO" },
  DEBUG: { tone: "neutral", label: "DEBUG" },
}

const eventTypeIcon: Record<EventSeverity, { icon: React.ReactNode; color: string }> = {
  success: { icon: <CheckCircle2 className="h-4 w-4" />, color: "var(--success)" },
  warning: { icon: <AlertTriangle className="h-4 w-4" />, color: "var(--warning)" },
  error: { icon: <XCircle className="h-4 w-4" />, color: "var(--danger)" },
  info: { icon: <Info className="h-4 w-4" />, color: "var(--info)" },
}

const severityConfig: Record<AlertSeverity, { tone: "danger" | "warning" | "info"; label: string }> = {
  critical: { tone: "danger", label: "Critical" },
  warning: { tone: "warning", label: "Warning" },
  info: { tone: "info", label: "Info" },
}

function serviceColor(id: string) {
  const colors = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)", "var(--chart-6)"]
  let hash = 0
  for (let i = 0; i < id.length; i++) hash = ((hash << 5) - hash) + id.charCodeAt(i)
  return colors[Math.abs(hash) % colors.length]
}

/* ──────────────────────────────────────────────
   Sub-components
   ────────────────────────────────────────────── */

function Sparkline({ data, color }: { data: MetricPoint[]; color?: string }) {
  return (
    <ResponsiveContainer width="100%" height={40}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id={`grad-${data[0]?.value ?? 0}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color ?? "var(--brand)"} stopOpacity={0.3} />
            <stop offset="100%" stopColor={color ?? "var(--brand)"} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area type="monotone" dataKey="value" stroke={color ?? "var(--brand)"} strokeWidth={1.5} fill={`url(#grad-${data[0]?.value ?? 0})`} dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  )
}

function MiniBarChart({ data }: { data: MetricPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={40}>
      <BarChart data={data}>
        <Bar dataKey="value" fill="var(--info)" radius={[2, 2, 0, 0]} opacity={0.7} />
      </BarChart>
    </ResponsiveContainer>
  )
}

function ServiceDetail({ service }: { service: ServiceHealth; onClose: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      className="overflow-hidden"
    >
      <div className="border-t border-[var(--border-subtle)] bg-[var(--bg-subtle)] p-4">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">Avg Response Time</p>
            <p className="mt-1 text-lg font-semibold text-[var(--text-primary)]">{service.responseTime}ms</p>
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">Uptime (24h)</p>
            <p className="mt-1 text-lg font-semibold text-[var(--text-primary)]">{service.uptime24h}%</p>
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">Requests (24h)</p>
            <p className="mt-1 text-lg font-semibold text-[var(--text-primary)]">{formatNumber(service.requests24h)}</p>
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">Errors (24h)</p>
            <p className="mt-1 text-lg font-semibold text-[var(--text-primary)]">{service.errors24h}</p>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

function InfraNodeDot({ status }: { status: string }) {
  return (
    <span
      className="inline-block h-2.5 w-2.5 rounded-full"
      style={{ backgroundColor: statusColor(status), boxShadow: `0 0 6px ${statusColor(status)}` }}
    />
  )
}

/* ──────────────────────────────────────────────
   Main Page
   ────────────────────────────────────────────── */

export default function OperationsPage() {
  const [timeRange, setTimeRange] = useState<TimeRange>("24h")
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [refreshInterval, setRefreshInterval] = useState<RefreshInterval>(30)
  const [activityFilter, setActivityFilter] = useState<EventSeverity | "all">("all")
  const [hasNewEvents, setHasNewEvents] = useState(false)
  const [alertTab, setAlertTab] = useState<TabId>("active")
  const [alertSearch, setAlertSearch] = useState("")
  const [logLevelFilter, setLogLevelFilter] = useState<LogLevel | "all">("all")
  const [logSearch, setLogSearch] = useState("")
  const [logServiceFilter, setLogServiceFilter] = useState("all")
  const [autoScrollLogs, setAutoScrollLogs] = useState(true)
  const [expandedService, setExpandedService] = useState<string | null>(null)
  const [selectedInfraNode, setSelectedInfraNode] = useState<string | null>(null)
  const [rules, setRules] = useState<AlertRule[]>(alertRules)
  const [alerts, setAlerts] = useState<Alert[]>(activeAlerts)
  const [logs] = useState<LogEntry[]>(logEntries)
  const [, setSimulatedTime] = useState(new Date())
  const logEndRef = useRef<HTMLDivElement>(null)
  const [newLogCount, setNewLogCount] = useState(0)

  const activityFeedRef = useRef<HTMLDivElement>(null)

  const uptime = 99.97
  const slaTarget = 99.95
  const avgResponseTime = 8
  const requestRate = 1240
  const errorRate = 0.89
  const activeServices = 8
  const totalServices = 10
  const queueDepth = 234

  const filteredEvents = useMemo(() => {
    if (activityFilter === "all") return activityEvents
    return activityEvents.filter((e) => e.type === activityFilter)
  }, [activityFilter])

  const filteredLogs = useMemo(() => {
    return logs.filter((l) => {
      if (logLevelFilter !== "all" && l.level !== logLevelFilter) return false
      if (logServiceFilter !== "all" && l.service !== logServiceFilter) return false
      if (logSearch && !l.message.toLowerCase().includes(logSearch.toLowerCase())) return false
      return true
    })
  }, [logs, logLevelFilter, logServiceFilter, logSearch])

  const uniqueServices = useMemo(() => [...new Set(logs.map((l) => l.service))], [logs])

  const filteredAlerts = useMemo(() => {
    if (!alertSearch) return alerts
    return alerts.filter(
      (a) =>
        a.title.toLowerCase().includes(alertSearch.toLowerCase()) ||
        a.service.toLowerCase().includes(alertSearch.toLowerCase()),
    )
  }, [alerts, alertSearch])

  const filteredResolved = useMemo(() => {
    if (!alertSearch) return resolvedAlerts
    return resolvedAlerts.filter(
      (a) =>
        a.title.toLowerCase().includes(alertSearch.toLowerCase()) ||
        a.service.toLowerCase().includes(alertSearch.toLowerCase()),
    )
  }, [alertSearch])

  const handleAcknowledgeAll = useCallback(() => {
    setAlerts((prev) => prev.map((a) => ({ ...a, acknowledged: true, acknowledgedBy: "You" })))
    toast.success("All alerts acknowledged")
  }, [])

  const handleAcknowledge = useCallback((id: string) => {
    setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, acknowledged: true, acknowledgedBy: "You" } : a)))
    toast.success("Alert acknowledged")
  }, [])

  const handleResolve = useCallback((id: string) => {
    setAlerts((prev) => prev.filter((a) => a.id !== id))
    toast.success("Alert resolved")
  }, [])

  const handleSnooze = useCallback((id: string) => {
    setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, acknowledged: true, acknowledgedBy: "You (snoozed)" } : a)))
    toast.success("Alert snoozed for 1 hour")
  }, [])

  const toggleRule = useCallback((id: string) => {
    setRules((prev) => prev.map((r) => (r.id === id ? { ...r, enabled: !r.enabled } : r)))
    toast.success("Alert rule updated")
  }, [])

  const scrollToBottom = useCallback(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [])

  useEffect(() => {
    if (autoScrollLogs && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: "smooth" })
    }
  }, [filteredLogs, autoScrollLogs])

  useEffect(() => {
    if (!autoRefresh) return
    const interval = setInterval(() => {
      setSimulatedTime(new Date())
      const r = Math.random()
      if (r > 0.7) {
        setHasNewEvents(true)
        setNewLogCount((c) => c + 1)
      }
    }, refreshInterval * 1000)
    return () => clearInterval(interval)
  }, [autoRefresh, refreshInterval])

  const handleNewEventsClick = useCallback(() => {
    setHasNewEvents(false)
    setNewLogCount(0)
    activityFeedRef.current?.scrollTo({ top: 0, behavior: "smooth" })
  }, [])

  const services = servicesData

  const groupedAlerts = useMemo(() => {
    const groups: Record<AlertSeverity, Alert[]> = { critical: [], warning: [], info: [] }
    for (const a of filteredAlerts) {
      if (!a.acknowledged) groups[a.severity].push(a)
    }
    return groups
  }, [filteredAlerts])

  const [copiedLog, setCopiedLog] = useState<string | null>(null)

  const handleCopyLog = useCallback(async (message: string) => {
    try {
      await navigator.clipboard.writeText(message)
      setCopiedLog(message)
      toast.success("Log copied to clipboard")
      setTimeout(() => setCopiedLog(null), 2000)
    } catch {
      toast.error("Failed to copy")
    }
  }, [])

  return (
    <div className="space-y-6 p-6">
      {/* ─── Header ─── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-[var(--text-primary)] sm:text-2xl">
            Operations Center
          </h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Real-time system observability and management
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Select value={timeRange} onValueChange={(v) => setTimeRange(v as TimeRange)}>
            <SelectTrigger className="w-[110px]">
              <Clock className="mr-1 h-3.5 w-3.5 text-[var(--text-tertiary)]" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1h">Last 1h</SelectItem>
              <SelectItem value="6h">Last 6h</SelectItem>
              <SelectItem value="24h">Last 24h</SelectItem>
              <SelectItem value="7d">Last 7d</SelectItem>
              <SelectItem value="30d">Last 30d</SelectItem>
              <SelectItem value="custom">Custom</SelectItem>
            </SelectContent>
          </Select>

          <div className="flex items-center gap-1 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-1">
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={clsx(
                "rounded-md p-1.5 transition-colors",
                autoRefresh
                  ? "text-[var(--brand)] bg-[var(--brand-soft)]"
                  : "text-[var(--text-tertiary)] hover:text-[var(--text-primary)]",
              )}
              title={autoRefresh ? "Disable auto-refresh" : "Enable auto-refresh"}
            >
              {autoRefresh ? <Bell className="h-3.5 w-3.5" /> : <BellOff className="h-3.5 w-3.5" />}
            </button>
            <span className="h-4 w-px bg-[var(--border-subtle)]" />
            <select
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(Number(e.target.value) as RefreshInterval)}
              className="border-0 bg-transparent py-1 pl-1 pr-5 text-xs text-[var(--text-secondary)] focus:outline-none cursor-pointer appearance-none"
            >
              <option value={10}>10s</option>
              <option value={30}>30s</option>
              <option value={60}>1m</option>
              <option value={300}>5m</option>
            </select>
          </div>

          <Button variant="secondary" size="sm" onClick={handleAcknowledgeAll}>
            <CheckCircle2 className="h-3.5 w-3.5" />
            Acknowledge All
          </Button>
        </div>
      </div>

      {/* ─── System Overview Row ─── */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <Card>
          <CardContent className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">Uptime</span>
              <Badge tone={uptime >= slaTarget ? "success" : "warning"}>{slaTarget}% SLA</Badge>
            </div>
            <p className="text-2xl font-bold text-[var(--text-primary)]">{uptime}%</p>
            <p className="text-[11px] text-[var(--text-tertiary)]">90-day rolling</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">Response Time</span>
              <Activity className="h-3.5 w-3.5 text-[var(--text-tertiary)]" />
            </div>
            <p className="text-2xl font-bold text-[var(--text-primary)]">{avgResponseTime}ms</p>
            <Sparkline data={generateSparkline(20, 8, 4)} color="var(--chart-2)" />
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">Request Rate</span>
              <Zap className="h-3.5 w-3.5 text-[var(--text-tertiary)]" />
            </div>
            <p className="text-2xl font-bold text-[var(--text-primary)]">{requestRate} <span className="text-sm font-normal text-[var(--text-tertiary)]">/s</span></p>
            <Sparkline data={generateSparkline(20, 1000, 300)} color="var(--chart-5)" />
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">Error Rate</span>
              <XCircle className="h-3.5 w-3.5 text-[var(--text-tertiary)]" />
            </div>
            <p
              className="text-2xl font-bold"
              style={{
                color: errorRate < 1 ? "var(--success)" : errorRate < 5 ? "var(--warning)" : "var(--danger)",
              }}
            >
              {errorRate}%
            </p>
            <Sparkline data={generateSparkline(20, errorRate, 0.5)} color={errorRate < 1 ? "var(--success)" : "var(--warning)"} />
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">Active Services</span>
              <Server className="h-3.5 w-3.5 text-[var(--text-tertiary)]" />
            </div>
            <p className="text-2xl font-bold text-[var(--text-primary)]">
              {activeServices}<span className="text-sm font-normal text-[var(--text-tertiary)]">/{totalServices}</span>
            </p>
            <div className="flex gap-1">
              {services.map((s) => (
                <span
                  key={s.name}
                  className="inline-block h-2 w-2 rounded-full"
                  style={{ backgroundColor: statusColor(s.status) }}
                />
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">Queue Depth</span>
              <Boxes className="h-3.5 w-3.5 text-[var(--text-tertiary)]" />
            </div>
            <p className="text-2xl font-bold text-[var(--text-primary)]">{queueDepth}</p>
            <MiniBarChart data={generateSparkline(12, queueDepth / 2, queueDepth / 3)} />
          </CardContent>
        </Card>
      </div>

      {/* ─── Service Health Grid ─── */}
      <Card>
        <CardHeader title="Service Health" description="Real-time status of all backend services" />
        <CardContent className="p-0">
          <div className="divide-y divide-[var(--border-subtle)]">
            {services.map((service) => (
              <div key={service.name}>
                <button
                  onClick={() => setExpandedService(expandedService === service.name ? null : service.name)}
                  className="flex w-full items-center gap-4 px-5 py-3.5 text-left transition-colors hover:bg-[var(--bg-hover)]"
                >
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-[var(--border-default)] bg-[var(--bg-subtle)] text-[var(--text-secondary)]">
                    {serviceIconMap[service.icon] ?? <Server className="h-4 w-4" />}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-[var(--text-primary)]">{service.name}</p>
                      <InfraNodeDot status={service.status} />
                    </div>
                    <p className="text-xs text-[var(--text-tertiary)]">Last check: {service.lastCheck}</p>
                  </div>
                  <div className="hidden items-center gap-6 sm:flex">
                    <div className="text-right">
                      <p className="text-xs text-[var(--text-tertiary)]">Response</p>
                      <p className="text-sm font-medium text-[var(--text-primary)]">{service.responseTime}ms</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-[var(--text-tertiary)]">Uptime</p>
                      <p className="text-sm font-medium text-[var(--text-primary)]">{service.uptime24h}%</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-[var(--text-tertiary)]">Requests</p>
                      <p className="text-sm font-medium text-[var(--text-primary)]">{formatNumber(service.requests24h)}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-[var(--text-tertiary)]">Errors</p>
                      <p className={clsx("text-sm font-medium", service.errors24h > 20 ? "text-[var(--danger)]" : "text-[var(--text-primary)]")}>{service.errors24h}</p>
                    </div>
                    <div className="w-24">
                      <Sparkline data={service.sparkline} color={statusColor(service.status)} />
                    </div>
                  </div>
                  <ChevronRight
                    className={clsx(
                      "h-4 w-4 shrink-0 text-[var(--text-tertiary)] transition-transform duration-200",
                      expandedService === service.name && "rotate-90",
                    )}
                  />
                </button>
                <AnimatePresence>
                  {expandedService === service.name && <ServiceDetail service={service} onClose={() => setExpandedService(null)} />}
                </AnimatePresence>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* ─── Activity Feed + Alerts ─── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Activity Feed */}
        <Card>
          <CardHeader
            title="Real-time Activity"
            description="Live system events and notifications"
            actions={
              <div className="flex items-center gap-2">
                {hasNewEvents && (
                  <motion.button
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    onClick={handleNewEventsClick}
                    className="flex items-center gap-1.5 rounded-full bg-[var(--brand-soft)] px-3 py-1 text-xs font-medium text-[var(--brand-strong)] transition-colors hover:bg-[var(--brand-border)]"
                  >
                    <Activity className="h-3 w-3" />
                    {newLogCount > 0 ? `${newLogCount} new` : "New events"}
                  </motion.button>
                )}
              </div>
            }
          />
          <div className="border-b border-[var(--border-subtle)] px-5 py-2">
            <div className="flex flex-wrap gap-1.5">
              {(["all", "success", "warning", "error", "info"] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => setActivityFilter(f)}
                  className={clsx(
                    "rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
                    activityFilter === f
                      ? "bg-[var(--brand-soft)] text-[var(--brand-strong)]"
                      : "text-[var(--text-tertiary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]",
                  )}
                >
                  {f === "all" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)}
                </button>
              ))}
            </div>
          </div>
          <div ref={activityFeedRef} className="max-h-[400px] overflow-y-auto">
            <div className="divide-y divide-[var(--border-subtle)]">
              <AnimatePresence initial={false}>
                {filteredEvents.map((event, index) => {
                  const info = eventTypeIcon[event.type]
                  return (
                    <motion.div
                      key={event.id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.03 }}
                      className="flex items-start gap-3 px-5 py-3"
                    >
                      <span className="mt-0.5 shrink-0" style={{ color: info.color }}>
                        {info.icon}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm text-[var(--text-primary)]">{event.description}</p>
                        <div className="mt-0.5 flex items-center gap-2 text-xs text-[var(--text-tertiary)]">
                          <span>{formatTime(event.timestamp)}</span>
                          <span className="text-[var(--border-strong)]">·</span>
                          <span>{event.source}</span>
                        </div>
                      </div>
                      <Badge tone={statusTone(event.status)}>{event.status}</Badge>
                    </motion.div>
                  )
                })}
              </AnimatePresence>
            </div>
          </div>
        </Card>

        {/* Alerts & Incidents Panel */}
        <Card>
          <CardHeader title="Alerts & Incidents" />
          <div className="border-b border-[var(--border-subtle)]">
            <div className="flex">
              {(["active", "history", "configure"] as TabId[]).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setAlertTab(tab)}
                  className={clsx(
                    "flex-1 px-4 py-2.5 text-xs font-medium transition-colors border-b-2",
                    alertTab === tab
                      ? "border-[var(--brand)] text-[var(--brand-strong)]"
                      : "border-transparent text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]",
                  )}
                >
                  {tab === "active" ? "Active Alerts" : tab === "history" ? "Alert History" : "Configure Alerts"}
                </button>
              ))}
            </div>
          </div>

          {alertTab === "active" && (
            <div className="max-h-[400px] overflow-y-auto">
              {(Object.entries(groupedAlerts) as [AlertSeverity, Alert[]][]).map(([severity, items]) =>
                items.length > 0 ? (
                  <div key={severity} className="px-5 py-3">
                    <div className="mb-2 flex items-center gap-2">
                      <div className="flex h-5 w-5 items-center justify-center rounded-full" style={{ backgroundColor: `color-mix(in srgb, ${severityConfig[severity].tone === "danger" ? "var(--danger)" : severityConfig[severity].tone === "warning" ? "var(--warning)" : "var(--info)"} 14%, transparent)` }}>
                        {severity === "critical" ? (
                          <AlertCircle className="h-3 w-3" style={{ color: "var(--danger)" }} />
                        ) : severity === "warning" ? (
                          <AlertTriangle className="h-3 w-3" style={{ color: "var(--warning)" }} />
                        ) : (
                          <Info className="h-3 w-3" style={{ color: "var(--info)" }} />
                        )}
                      </div>
                      <span className="text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
                        {severityConfig[severity].label}{" "}
                        <span className="ml-1 rounded bg-[var(--bg-subtle)] px-1.5 py-0.5 text-[10px]">
                          {items.length}
                        </span>
                      </span>
                    </div>
                    <div className="space-y-2">
                      {items.map((alert) => (
                        <motion.div
                          key={alert.id}
                          layout
                          initial={{ opacity: 0, y: 5 }}
                          animate={{ opacity: 1, y: 0 }}
                          className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-subtle)] p-3"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0">
                              <div className="flex items-center gap-2">
                                <Badge tone={severityConfig[alert.severity].tone}>{severityConfig[alert.severity].label}</Badge>
                                <span className="text-xs text-[var(--text-tertiary)]">{alert.id}</span>
                              </div>
                              <p className="mt-1 text-sm font-medium text-[var(--text-primary)]">{alert.title}</p>
                              <p className="mt-0.5 text-xs text-[var(--text-secondary)]">{alert.description}</p>
                              <div className="mt-1.5 flex items-center gap-2 text-[11px] text-[var(--text-tertiary)]">
                                <span>{formatTime(alert.timestamp)}</span>
                                <span className="text-[var(--border-strong)]">·</span>
                                <span>{alert.service}</span>
                                {alert.acknowledged && (
                                  <>
                                    <span className="text-[var(--border-strong)]">·</span>
                                    <span className="text-[var(--success)]">Acknowledged by {alert.acknowledgedBy}</span>
                                  </>
                                )}
                              </div>
                            </div>
                          </div>
                          <div className="mt-2 flex items-center gap-1.5">
                            {!alert.acknowledged && (
                              <>
                                <Button variant="ghost" size="sm" onClick={() => handleAcknowledge(alert.id)}>
                                  <CheckCircle2 className="h-3 w-3" />
                                  Acknowledge
                                </Button>
                                <Button variant="ghost" size="sm" onClick={() => handleSnooze(alert.id)}>
                                  <Clock className="h-3 w-3" />
                                  Snooze
                                </Button>
                              </>
                            )}
                            <Button variant="ghost" size="sm" onClick={() => handleResolve(alert.id)}>
                              <XCircle className="h-3 w-3" />
                              Resolve
                            </Button>
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  </div>
                ) : null,
              )}
              {Object.values(groupedAlerts).every((g) => g.length === 0) && (
                <div className="flex flex-col items-center py-12 text-center">
                  <ShieldCheck className="mb-2 h-8 w-8 text-[var(--success)]" />
                  <p className="text-sm font-medium text-[var(--text-primary)]">No active alerts</p>
                  <p className="text-xs text-[var(--text-tertiary)]">All systems operating normally</p>
                </div>
              )}
            </div>
          )}

          {alertTab === "history" && (
            <div className="p-5">
              <div className="mb-3 flex items-center gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--text-tertiary)]" />
                  <input
                    type="text"
                    placeholder="Search alerts..."
                    value={alertSearch}
                    onChange={(e) => setAlertSearch(e.target.value)}
                    className="w-full rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] py-2 pl-8 pr-3 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
                  />
                </div>
              </div>
              <div className="max-h-[340px] overflow-y-auto">
                <Table>
                  <THead>
                    <TR>
                      <TH>ID</TH>
                      <TH>Title</TH>
                      <TH>Service</TH>
                      <TH>Duration</TH>
                      <TH>Ack By</TH>
                      <TH>Resolved</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {filteredResolved.map((alert) => (
                      <TR key={alert.id}>
                        <TD><span className="text-xs font-mono text-[var(--text-tertiary)]">{alert.id}</span></TD>
                        <TD>
                          <div className="flex items-center gap-2">
                            <Badge tone={severityConfig[alert.severity].tone}>{severityConfig[alert.severity].label}</Badge>
                            <span className="text-sm">{alert.title}</span>
                          </div>
                        </TD>
                        <TD><span className="text-sm text-[var(--text-secondary)]">{alert.service}</span></TD>
                        <TD><span className="text-sm">{alert.duration}</span></TD>
                        <TD><span className="text-sm">{alert.acknowledgedBy}</span></TD>
                        <TD><span className="text-xs text-[var(--text-tertiary)]">{alert.resolvedAt ? formatTime(alert.resolvedAt) : "-"}</span></TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              </div>
            </div>
          )}

          {alertTab === "configure" && (
            <div className="p-5">
              <div className="space-y-2">
                {rules.map((rule) => (
                  <div
                    key={rule.id}
                    className="flex items-center justify-between rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-subtle)] p-3"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-[var(--text-primary)]">{rule.name}</span>
                        <Badge tone={rule.enabled ? "success" : "neutral"}>{rule.enabled ? "Enabled" : "Disabled"}</Badge>
                      </div>
                      <p className="text-xs text-[var(--text-tertiary)]">
                        {rule.metric} {rule.condition} {rule.threshold}
                      </p>
                    </div>
                    <button
                      onClick={() => toggleRule(rule.id)}
                      className="shrink-0 text-[var(--text-tertiary)] transition-colors hover:text-[var(--text-primary)]"
                    >
                      {rule.enabled ? <ToggleRight className="h-6 w-6 text-[var(--brand)]" /> : <ToggleLeft className="h-6 w-6" />}
                    </button>
                  </div>
                ))}
              </div>
              <Button variant="secondary" size="sm" className="mt-3 w-full">
                <Plus className="h-3.5 w-3.5" />
                Add Alert Rule
              </Button>
            </div>
          )}
        </Card>
      </div>

      {/* ─── Resource Usage Charts ─── */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="CPU Usage (%)" description="Per-service CPU utilization over time" />
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={resourceChartData}>
                  <XAxis dataKey="time" tick={{ fontSize: 11, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "var(--bg-surface-elevated)",
                      border: "1px solid var(--border-default)",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                  />
                  {["API Gateway", "ML Engine", "Database", "Redis", "RabbitMQ"].map((key) => (
                    <Line key={key} type="monotone" dataKey={key} stroke={serviceColor(key)} strokeWidth={1.5} dot={false} opacity={0.8} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader title="Memory Usage (GB)" description="Memory consumption trend" />
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={resourceChartData}>
                  <defs>
                    <linearGradient id="memGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--chart-2)" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="var(--chart-2)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="time" tick={{ fontSize: 11, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "var(--bg-surface-elevated)",
                      border: "1px solid var(--border-default)",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                  />
                  <Area type="monotone" dataKey="API Gateway" stroke="var(--chart-1)" fill="url(#memGrad)" stackId="1" />
                  <Area type="monotone" dataKey="ML Engine" stroke="var(--chart-4)" fill="url(#memGrad)" stackId="1" />
                  <Area type="monotone" dataKey="Database" stroke="var(--chart-3)" fill="url(#memGrad)" stackId="1" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader title="Network I/O (Mbps)" description="Inbound / Outbound traffic" />
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={networkData}>
                  <defs>
                    <linearGradient id="inGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--chart-1)" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="var(--chart-1)" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="outGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--chart-5)" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="var(--chart-5)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="time" tick={{ fontSize: 11, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "var(--bg-surface-elevated)",
                      border: "1px solid var(--border-default)",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                  />
                  <Area type="monotone" dataKey="inbound" stroke="var(--chart-1)" fill="url(#inGrad)" strokeWidth={1.5} dot={false} />
                  <Area type="monotone" dataKey="outbound" stroke="var(--chart-5)" fill="url(#outGrad)" strokeWidth={1.5} dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader title="Disk I/O (IOPS)" description="Read / Write operations" />
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={diskData} barGap={2}>
                  <XAxis dataKey="time" tick={{ fontSize: 11, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "var(--bg-surface-elevated)",
                      border: "1px solid var(--border-default)",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                  />
                  <Bar dataKey="read" fill="var(--chart-3)" radius={[2, 2, 0, 0]} opacity={0.8} />
                  <Bar dataKey="write" fill="var(--chart-6)" radius={[2, 2, 0, 0]} opacity={0.8} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ─── Infrastructure Map ─── */}
      <Card>
        <CardHeader
          title="Infrastructure Map"
          description="Service topology with real-time status"
          actions={
            <Button variant="ghost" size="sm">
              <ExternalLink className="h-3.5 w-3.5" />
              Full Topology
            </Button>
          }
        />
        <CardContent>
          <div className="relative h-[300px] w-full overflow-hidden rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-subtle)]">
            <svg className="absolute inset-0 h-full w-full">
              {infraNodes.flatMap((node) =>
                node.connections.map((targetId) => {
                  const target = infraNodes.find((n) => n.id === targetId)
                  if (!target) return null
                  return (
                    <line
                      key={`${node.id}-${targetId}`}
                      x1={`${node.x}%`}
                      y1={`${node.y}%`}
                      x2={`${target.x}%`}
                      y2={`${target.y}%`}
                      stroke="var(--border-default)"
                      strokeWidth={1.5}
                      strokeDasharray="4 2"
                    />
                  )
                }),
              )}
            </svg>
            {infraNodes.map((node) => (
              <motion.button
                key={node.id}
                onClick={() => setSelectedInfraNode(selectedInfraNode === node.id ? null : node.id)}
                className={clsx(
                  "absolute flex items-center gap-2 rounded-lg border-2 px-3 py-2 text-left transition-all",
                  selectedInfraNode === node.id
                    ? "border-[var(--brand)] bg-[var(--brand-soft)] shadow-[var(--shadow-md)]"
                    : "border-[var(--border-default)] bg-[var(--bg-surface)] hover:shadow-[var(--shadow-sm)]",
                )}
                style={{
                  left: `${node.x}%`,
                  top: `${node.y}%`,
                  transform: "translate(-50%, -50%)",
                  borderColor: selectedInfraNode === node.id ? "var(--brand)" : statusColor(node.status),
                }}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.97 }}
              >
                <span
                  className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{ backgroundColor: statusColor(node.status) }}
                />
                <span className="text-xs font-medium text-[var(--text-primary)]">{node.name}</span>
              </motion.button>
            ))}
            {selectedInfraNode && (
              <motion.div
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                className="absolute bottom-3 left-3 right-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface-elevated)] p-3 shadow-[var(--shadow-md)]"
              >
                {(() => {
                  const svc = services.find((s) => s.name === infraNodes.find((n) => n.id === selectedInfraNode)?.name)
                  if (!svc) return null
                  return (
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <InfraNodeDot status={svc.status} />
                        <span className="font-medium text-[var(--text-primary)]">{svc.name}</span>
                        <span className="text-[var(--text-tertiary)]">·</span>
                        <span className="text-[var(--text-tertiary)]">{svc.responseTime}ms</span>
                        <span className="text-[var(--text-tertiary)]">·</span>
                        <span className="text-[var(--text-tertiary)]">{svc.uptime24h}% uptime</span>
                      </div>
                      <Badge tone={statusTone(svc.status)}>{svc.status}</Badge>
                    </div>
                  )
                })()}
              </motion.div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* ─── Logs Viewer ─── */}
      <Card>
        <CardHeader
          title="Logs"
          description="Real-time log stream from all services"
          actions={
            <div className="flex items-center gap-2">
              <button
                onClick={() => setAutoScrollLogs(!autoScrollLogs)}
                className={clsx(
                  "rounded-md p-1.5 transition-colors",
                  autoScrollLogs
                    ? "text-[var(--brand)] bg-[var(--brand-soft)]"
                    : "text-[var(--text-tertiary)] hover:text-[var(--text-primary)]",
                )}
                title={autoScrollLogs ? "Disable auto-scroll" : "Enable auto-scroll"}
              >
                {autoScrollLogs ? <ArrowDown className="h-3.5 w-3.5" /> : <ArrowUp className="h-3.5 w-3.5" />}
              </button>
              <button
                onClick={scrollToBottom}
                className="rounded-md p-1.5 text-[var(--text-tertiary)] transition-colors hover:text-[var(--text-primary)]"
                title="Scroll to bottom"
              >
                <ChevronDown className="h-3.5 w-3.5" />
              </button>
            </div>
          }
        />
        <div className="border-b border-[var(--border-subtle)] px-5 py-2.5">
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex gap-1 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-0.5">
              {(["all", "ERROR", "WARN", "INFO", "DEBUG"] as const).map((level) => (
                <button
                  key={level}
                  onClick={() => setLogLevelFilter(level)}
                  className={clsx(
                    "rounded-md px-2 py-1 text-xs font-medium transition-colors",
                    logLevelFilter === level
                      ? "bg-[var(--brand-soft)] text-[var(--brand-strong)]"
                      : "text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]",
                  )}
                >
                  {level === "all" ? "All" : level}
                </button>
              ))}
            </div>

            <div className="relative flex-1 min-w-[120px] max-w-[200px]">
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--text-tertiary)]" />
              <input
                type="text"
                placeholder="Search logs..."
                value={logSearch}
                onChange={(e) => setLogSearch(e.target.value)}
                className="w-full rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] py-1.5 pl-8 pr-3 text-xs text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
              />
            </div>

            <select
              value={logServiceFilter}
              onChange={(e) => setLogServiceFilter(e.target.value)}
              className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-2 py-1.5 text-xs text-[var(--text-secondary)] focus:outline-none cursor-pointer"
            >
              <option value="all">All Services</option>
              {uniqueServices.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="max-h-[400px] overflow-y-auto">
          <div className="divide-y divide-[var(--border-subtle)] font-mono text-xs">
            {filteredLogs.map((log) => {
              const levelInfo = logLevelBadge[log.level]
              return (
                <motion.div
                  key={log.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="group flex items-start gap-3 px-5 py-2 transition-colors hover:bg-[var(--bg-hover)]"
                >
                  <span className="shrink-0 text-[11px] text-[var(--text-tertiary)] tabular-nums">{log.timestamp}</span>
                  <Badge tone={levelInfo.tone} className="shrink-0 text-[10px] uppercase">
                    {levelInfo.label}
                  </Badge>
                  <span className="shrink-0 text-[var(--text-tertiary)]">{log.service}</span>
                  <span className="flex-1 text-[var(--text-primary)]">{log.message}</span>
                  <button
                    onClick={() => handleCopyLog(log.message)}
                    className="shrink-0 opacity-0 transition-opacity group-hover:opacity-100"
                    title="Copy log line"
                  >
                    {copiedLog === log.message ? (
                      <CheckCircle2 className="h-3.5 w-3.5 text-[var(--success)]" />
                    ) : (
                      <Copy className="h-3.5 w-3.5 text-[var(--text-tertiary)]" />
                    )}
                  </button>
                </motion.div>
              )
            })}
          </div>
          <div ref={logEndRef} />
        </div>
      </Card>
    </div>
  )
}
