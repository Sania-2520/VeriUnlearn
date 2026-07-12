"use client"

import { useEffect, useState, useCallback, useRef } from "react"
import {
  getSystemHealth,
  getInferenceMetrics,
  getControllerHealth,
  getRegistryStats,
} from "@/lib/api/client"
import {
  Activity,
  Cpu,
  HardDrive,
  Zap,
  Clock,
  AlertCircle,
  RefreshCw,
  CheckCircle,
  XCircle,
  Thermometer,
  Gauge,
  Server,
} from "lucide-react"

interface SystemHealth {
  status: string
  gpu?: {
    name: string
    memory_used_mb: number
    memory_total_mb: number
    utilization_percent: number
    temperature_c: number
  }
  cpu?: {
    cores: number
    usage_percent: number
  }
  memory?: {
    used_mb: number
    total_mb: number
  }
  disk?: {
    used_gb: number
    total_gb: number
  }
}

interface InferenceMetrics {
  latency_p50_ms: number
  latency_p95_ms: number
  latency_p99_ms: number
  throughput_rps: number
  total_requests: number
  error_rate: number
}

interface ControllerHealth {
  status: string
  active_workers: number
  queue_depth: number
  training_jobs_running: number
  training_jobs_queued: number
  unlearning_jobs_running: number
  unlearning_jobs_queued: number
  uptime_seconds: number
}

interface RegistryStats {
  total_models: number
  total_versions: number
  active_versions: number
  archived_versions: number
}

function StatusDot({ status }: { status: string }) {
  const color = status === "healthy" || status === "ok"
    ? "bg-emerald-400"
    : status === "degraded"
      ? "bg-yellow-400"
      : "bg-red-400"
  return <span className={`h-2 w-2 rounded-full ${color} inline-block`} />
}

function ProgressBar({ value, max, color }: { value: number; max: number; color?: string }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0
  const barColor = color || (pct > 80 ? "bg-red-500" : pct > 60 ? "bg-yellow-500" : "bg-emerald-500")
  return (
    <div className="w-full h-2 bg-[#2f2f2f] rounded-full overflow-hidden">
      <div className={`h-full ${barColor} rounded-full transition-all duration-500`} style={{ width: `${pct}%` }} />
    </div>
  )
}

function MetricCard({ icon: Icon, label, value, sub }: { icon: any; label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-[#171717] border border-[#2f2f2f]/60 rounded-xl p-4">
      <div className="flex items-center gap-2 text-xs text-gray-500 uppercase tracking-wider font-semibold mb-2">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
      <p className="text-xl font-bold text-white">{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-0.5">{sub}</p>}
    </div>
  )
}

export default function MonitoringPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null)
  const [inference, setInference] = useState<InferenceMetrics | null>(null)
  const [controller, setController] = useState<ControllerHealth | null>(null)
  const [registry, setRegistry] = useState<RegistryStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date())
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchAll = useCallback(async () => {
    setError(null)
    try {
      const [healthRes, inferenceRes, controllerRes, registryRes] = await Promise.allSettled([
        getSystemHealth(),
        getInferenceMetrics(),
        getControllerHealth(),
        getRegistryStats(),
      ])
      if (healthRes.status === "fulfilled") setHealth(healthRes.value)
      if (inferenceRes.status === "fulfilled") setInference(inferenceRes.value)
      if (controllerRes.status === "fulfilled") setController(controllerRes.value)
      if (registryRes.status === "fulfilled") setRegistry(registryRes.value)
      setLastRefresh(new Date())
    } catch {
      setError("Failed to fetch monitoring data")
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAll()
    intervalRef.current = setInterval(fetchAll, 15000)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [fetchAll])

  const formatUptime = (seconds: number) => {
    const d = Math.floor(seconds / 86400)
    const h = Math.floor((seconds % 86400) / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    if (d > 0) return `${d}d ${h}h ${m}m`
    if (h > 0) return `${h}h ${m}m`
    return `${m}m`
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">System Monitoring</h1>
          <p className="text-sm text-gray-400 mt-1">Real-time system health and performance metrics</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500">
            Last refresh: {lastRefresh.toLocaleTimeString()}
          </span>
          <button
            onClick={fetchAll}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-300 hover:text-white bg-[#2f2f2f] hover:bg-[#3a3a3a] border border-[#2f2f2f] hover:border-gray-500 rounded-lg transition-colors cursor-pointer"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-950/30 border border-red-900/40 rounded-lg text-sm text-red-400">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin h-8 w-8 border-2 border-emerald-500 border-t-transparent rounded-full" />
        </div>
      ) : (
        <>
          {/* System Health Overview */}
          <div className="flex items-center gap-4 p-4 bg-[#171717] border border-[#2f2f2f]/60 rounded-xl">
            <div className="flex items-center gap-2">
              <StatusDot status={health?.status || "unknown"} />
              <span className="text-sm font-medium text-gray-200">
                System: {health?.status || "Unknown"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <StatusDot status={controller?.status || "unknown"} />
              <span className="text-sm font-medium text-gray-200">
                Controller: {controller?.status || "Unknown"}
              </span>
            </div>
            {controller && (
              <div className="flex items-center gap-1.5 ml-auto text-xs text-gray-400">
                <Clock className="h-3.5 w-3.5" />
                Uptime: {formatUptime(controller.uptime_seconds)}
              </div>
            )}
          </div>

          {/* GPU & Resource Metrics */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {health?.gpu && (
              <>
                <MetricCard icon={Cpu} label="GPU Utilization" value={`${health.gpu.utilization_percent.toFixed(1)}%`} sub={health.gpu.name} />
                <MetricCard icon={HardDrive} label="GPU Memory" value={`${(health.gpu.memory_used_mb / 1024).toFixed(1)} / ${(health.gpu.memory_total_mb / 1024).toFixed(1)} GB`} />
                <MetricCard icon={Thermometer} label="GPU Temp" value={`${health.gpu.temperature_c}°C`} />
              </>
            )}
            {health?.cpu && (
              <MetricCard icon={Server} label="CPU Usage" value={`${health.cpu.usage_percent.toFixed(1)}%`} sub={`${health.cpu.cores} cores`} />
            )}
            {!health?.gpu && !health?.cpu && (
              <>
                <MetricCard icon={Cpu} label="GPU Utilization" value="--" sub="No data" />
                <MetricCard icon={HardDrive} label="GPU Memory" value="--" sub="No data" />
                <MetricCard icon={Thermometer} label="GPU Temp" value="--" sub="No data" />
                <MetricCard icon={Server} label="CPU Usage" value="--" sub="No data" />
              </>
            )}
          </div>

          {/* GPU Memory & Disk Progress */}
          {health?.gpu && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="bg-[#171717] border border-[#2f2f2f]/60 rounded-xl p-4">
                <div className="flex justify-between text-xs text-gray-400 mb-2">
                  <span>GPU Memory</span>
                  <span>{(health.gpu.memory_used_mb / 1024).toFixed(1)} / {(health.gpu.memory_total_mb / 1024).toFixed(1)} GB</span>
                </div>
                <ProgressBar value={health.gpu.memory_used_mb} max={health.gpu.memory_total_mb} />
              </div>
              {health.disk && (
                <div className="bg-[#171717] border border-[#2f2f2f]/60 rounded-xl p-4">
                  <div className="flex justify-between text-xs text-gray-400 mb-2">
                    <span>Disk Usage</span>
                    <span>{health.disk.used_gb.toFixed(1)} / {health.disk.total_gb.toFixed(1)} GB</span>
                  </div>
                  <ProgressBar value={health.disk.used_gb} max={health.disk.total_gb} />
                </div>
              )}
            </div>
          )}

          {/* Inference Metrics */}
          <div className="bg-[#171717] border border-[#2f2f2f]/60 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <Zap className="h-4 w-4 text-emerald-500" />
              <h2 className="text-sm font-semibold text-gray-200">Inference Metrics</h2>
            </div>
            {inference ? (
              <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                <div className="p-3 bg-[#212121] border border-[#2f2f2f] rounded-lg">
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">P50 Latency</p>
                  <p className="text-lg font-bold text-white">{inference.latency_p50_ms.toFixed(1)} ms</p>
                </div>
                <div className="p-3 bg-[#212121] border border-[#2f2f2f] rounded-lg">
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">P95 Latency</p>
                  <p className="text-lg font-bold text-white">{inference.latency_p95_ms.toFixed(1)} ms</p>
                </div>
                <div className="p-3 bg-[#212121] border border-[#2f2f2f] rounded-lg">
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">P99 Latency</p>
                  <p className="text-lg font-bold text-white">{inference.latency_p99_ms.toFixed(1)} ms</p>
                </div>
                <div className="p-3 bg-[#212121] border border-[#2f2f2f] rounded-lg">
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">Throughput</p>
                  <p className="text-lg font-bold text-white">{inference.throughput_rps.toFixed(1)} <span className="text-xs text-gray-400">req/s</span></p>
                </div>
                <div className="p-3 bg-[#212121] border border-[#2f2f2f] rounded-lg">
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">Total Requests</p>
                  <p className="text-lg font-bold text-white">{inference.total_requests.toLocaleString()}</p>
                </div>
                <div className="p-3 bg-[#212121] border border-[#2f2f2f] rounded-lg">
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">Error Rate</p>
                  <p className={`text-lg font-bold ${inference.error_rate > 0.05 ? "text-red-400" : "text-emerald-400"}`}>
                    {(inference.error_rate * 100).toFixed(2)}%
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-500">No inference data available</p>
            )}
          </div>

          {/* Queue Status */}
          <div className="bg-[#171717] border border-[#2f2f2f]/60 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <Activity className="h-4 w-4 text-emerald-500" />
              <h2 className="text-sm font-semibold text-gray-200">Queue Status</h2>
            </div>
            {controller ? (
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="p-3 bg-[#212121] border border-[#2f2f2f] rounded-lg">
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">Active Workers</p>
                  <p className="text-lg font-bold text-emerald-400">{controller.active_workers}</p>
                </div>
                <div className="p-3 bg-[#212121] border border-[#2f2f2f] rounded-lg">
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">Queue Depth</p>
                  <p className="text-lg font-bold text-white">{controller.queue_depth}</p>
                </div>
                <div className="p-3 bg-[#212121] border border-[#2f2f2f] rounded-lg">
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">Training</p>
                  <div className="flex items-baseline gap-1.5">
                    <p className="text-lg font-bold text-yellow-400">{controller.training_jobs_running}</p>
                    <span className="text-xs text-gray-500">running</span>
                    <span className="text-gray-600">/</span>
                    <p className="text-lg font-bold text-gray-400">{controller.training_jobs_queued}</p>
                    <span className="text-xs text-gray-500">queued</span>
                  </div>
                </div>
                <div className="p-3 bg-[#212121] border border-[#2f2f2f] rounded-lg">
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">Unlearning</p>
                  <div className="flex items-baseline gap-1.5">
                    <p className="text-lg font-bold text-yellow-400">{controller.unlearning_jobs_running}</p>
                    <span className="text-xs text-gray-500">running</span>
                    <span className="text-gray-600">/</span>
                    <p className="text-lg font-bold text-gray-400">{controller.unlearning_jobs_queued}</p>
                    <span className="text-xs text-gray-500">queued</span>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-500">No controller data available</p>
            )}
          </div>

          {/* Registry Stats */}
          {registry && (
            <div className="bg-[#171717] border border-[#2f2f2f]/60 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-4">
                <Gauge className="h-4 w-4 text-emerald-500" />
                <h2 className="text-sm font-semibold text-gray-200">Model Registry</h2>
              </div>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="p-3 bg-[#212121] border border-[#2f2f2f] rounded-lg">
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">Total Models</p>
                  <p className="text-lg font-bold text-white">{registry.total_models}</p>
                </div>
                <div className="p-3 bg-[#212121] border border-[#2f2f2f] rounded-lg">
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">Total Versions</p>
                  <p className="text-lg font-bold text-white">{registry.total_versions}</p>
                </div>
                <div className="p-3 bg-[#212121] border border-[#2f2f2f] rounded-lg">
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">Active</p>
                  <p className="text-lg font-bold text-emerald-400">{registry.active_versions}</p>
                </div>
                <div className="p-3 bg-[#212121] border border-[#2f2f2f] rounded-lg">
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">Archived</p>
                  <p className="text-lg font-bold text-gray-400">{registry.archived_versions}</p>
                </div>
              </div>
            </div>
          )}

          <p className="text-[11px] text-gray-500 text-center">Auto-refreshing every 15 seconds</p>
        </>
      )}
    </div>
  )
}
