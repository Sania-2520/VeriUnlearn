"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import AuthGuard from "../../components/AuthGuard";
import Navbar from "../../components/Navbar";
import { api } from "../../lib/api";

interface OperationsStats {
  total_jobs: number;
  running_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  queue_size: number;
  workers_active: number;
  avg_latency_ms: number;
  success_rate: number;
}

interface SystemMetrics {
  cpu_percent: number;
  memory_percent: number;
  disk_percent: number;
  gpu_percent: number | null;
  gpu_memory_percent: number | null;
  network_io: Record<string, number>;
}

interface WorkerStatus {
  worker_id: string;
  status: string;
  current_task: string | null;
  memory_mb: number;
  cpu_percent: number;
  uptime_seconds: number;
}

interface HealthCheck {
  status: string;
  version: string;
  checks: Record<string, Record<string, unknown>>;
  timestamp: string;
}

interface ReadinessCheck {
  status: string;
  ready: boolean;
  checks: Record<string, unknown>;
}

interface LivenessCheck {
  status: string;
  uptime_seconds: number;
  pid: number;
}

interface LogEntry {
  trace_id: string | null;
  request_id: string | null;
  timestamp: string;
  component: string;
  severity: string;
  message: string;
  duration_ms: number | null;
}

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function severityColor(s: string): string {
  switch (s?.toLowerCase()) {
    case "error":
      return "bg-red-100 text-red-700";
    case "warning":
      return "bg-yellow-100 text-yellow-700";
    case "info":
      return "bg-blue-100 text-blue-700";
    default:
      return "bg-gray-100 text-gray-500";
  }
}

function statusDot(s: string): string {
  switch (s) {
    case "healthy":
    case "ready":
      return "bg-green-500";
    case "degraded":
      return "bg-yellow-500";
    case "not_ready":
    case "unhealthy":
      return "bg-red-500";
    default:
      return "bg-gray-400";
  }
}

function ProgressBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full transition-all ${color}`}
        style={{ width: `${Math.min(value, 100)}%` }}
      />
    </div>
  );
}

function MetricCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
      {children}
    </div>
  );
}

export default function OperationsPage() {
  const [logLevel, setLogLevel] = useState<string>("");
  const [logSearch, setLogSearch] = useState("");

  const { data: health } = useQuery<HealthCheck>({
    queryKey: ["mlops", "health"],
    queryFn: async () => api.mlops.health() as Promise<HealthCheck>,
    refetchInterval: 30000,
  });

  const { data: readiness } = useQuery<ReadinessCheck>({
    queryKey: ["mlops", "readiness"],
    queryFn: async () => api.mlops.readiness() as Promise<ReadinessCheck>,
    refetchInterval: 30000,
  });

  const { data: liveness } = useQuery<LivenessCheck>({
    queryKey: ["mlops", "liveness"],
    queryFn: async () => api.mlops.liveness() as Promise<LivenessCheck>,
    refetchInterval: 30000,
  });

  const { data: opsStats } = useQuery<OperationsStats>({
    queryKey: ["mlops", "operations"],
    queryFn: async () => api.mlops.operations() as Promise<OperationsStats>,
    refetchInterval: 15000,
  });

  const { data: sysMetrics } = useQuery<SystemMetrics>({
    queryKey: ["mlops", "metrics"],
    queryFn: async () => api.mlops.systemMetrics() as Promise<SystemMetrics>,
    refetchInterval: 15000,
  });

  const { data: workersData, isLoading: workersLoading } = useQuery<WorkerStatus[]>({
    queryKey: ["mlops", "workers"],
    queryFn: async () => api.mlops.workers() as Promise<WorkerStatus[]>,
    refetchInterval: 15000,
  });
  const workers: WorkerStatus[] = workersData ?? [];

  const { data: logsData, isLoading: logsLoading } = useQuery<LogEntry[]>({
    queryKey: ["mlops", "logs", logLevel, logSearch],
    queryFn: async () => api.mlops.logs({ level: logLevel || undefined, query: logSearch || undefined, limit: 50 }) as Promise<LogEntry[]>,
    refetchInterval: 10000,
  });
  const logs: LogEntry[] = logsData ?? [];

  const { data: modelStats } = useQuery<{ loaded_models: number; total_requests: number; cache_hits: number; avg_latency_ms: number }>({
    queryKey: ["mlops", "modelStats"],
    queryFn: async () => api.mlops.modelStats() as Promise<{ loaded_models: number; total_requests: number; cache_hits: number; avg_latency_ms: number }>,
    refetchInterval: 30000,
  });

  const { data: configData } = useQuery<{ app_env: string; version: string; features: Record<string, boolean>; services: Record<string, string> }>({
    queryKey: ["mlops", "config"],
    queryFn: async () => api.mlops.config() as Promise<{ app_env: string; version: string; features: Record<string, boolean>; services: Record<string, string> }>,
  });
  const config = configData;

  return (
    <AuthGuard>
      <Navbar />
      <main className="min-h-screen p-8 max-w-7xl mx-auto space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Operations</h1>
          <p className="text-gray-500 mt-1">MLOps health, metrics, and pipeline monitoring</p>
        </div>

        {/* Status Bar */}
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${statusDot(health?.status ?? "unknown")}`} />
            <div>
              <p className="text-sm font-medium text-gray-900">Health</p>
              <p className="text-xs text-gray-500">{health?.status ?? "loading"} &middot; v{health?.version ?? "-"}</p>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${statusDot(readiness?.status ?? "unknown")}`} />
            <div>
              <p className="text-sm font-medium text-gray-900">Readiness</p>
              <p className="text-xs text-gray-500">{readiness?.status ?? "loading"} &middot; {readiness?.ready ? "Ready" : "Not Ready"}</p>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-green-500" />
            <div>
              <p className="text-sm font-medium text-gray-900">Liveness</p>
              <p className="text-xs text-gray-500">up {liveness ? formatUptime(liveness.uptime_seconds) : "-"} &middot; PID {liveness?.pid ?? "-"}</p>
            </div>
          </div>
        </div>

        {/* Operations Stats */}
        <Section title="Operations Overview">
          <div className="grid grid-cols-4 gap-4">
            <MetricCard label="Total Jobs" value={opsStats?.total_jobs ?? 0} />
            <MetricCard label="Running" value={opsStats?.running_jobs ?? 0} sub={`${opsStats?.queue_size ?? 0} in queue`} />
            <MetricCard label="Completed" value={opsStats?.completed_jobs ?? 0} />
            <MetricCard label="Failed" value={opsStats?.failed_jobs ?? 0} sub={`${opsStats?.avg_latency_ms ?? 0}ms avg`} />
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-500">Success Rate</span>
              <span className="text-sm font-medium text-gray-900">{opsStats?.success_rate ?? 0}%</span>
            </div>
            <ProgressBar
              value={opsStats?.success_rate ?? 0}
              color={(opsStats?.success_rate ?? 0) >= 90 ? "bg-green-500" : (opsStats?.success_rate ?? 0) >= 70 ? "bg-yellow-500" : "bg-red-500"}
            />
          </div>
        </Section>

        {/* System Metrics */}
        <Section title="System Metrics">
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">CPU</span>
                <span className="font-medium text-gray-900">{sysMetrics?.cpu_percent?.toFixed(1) ?? "-"}%</span>
              </div>
              <ProgressBar value={sysMetrics?.cpu_percent ?? 0} color="bg-blue-500" />
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Memory</span>
                <span className="font-medium text-gray-900">{sysMetrics?.memory_percent?.toFixed(1) ?? "-"}%</span>
              </div>
              <ProgressBar value={sysMetrics?.memory_percent ?? 0} color="bg-purple-500" />
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Disk</span>
                <span className="font-medium text-gray-900">{sysMetrics?.disk_percent?.toFixed(1) ?? "-"}%</span>
              </div>
              <ProgressBar value={sysMetrics?.disk_percent ?? 0} color="bg-orange-500" />
            </div>
          </div>
          {sysMetrics?.gpu_percent != null && (
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">GPU</span>
                  <span className="font-medium text-gray-900">{sysMetrics.gpu_percent?.toFixed(1)}%</span>
                </div>
                <ProgressBar value={sysMetrics.gpu_percent} color="bg-green-500" />
              </div>
              {sysMetrics.gpu_memory_percent != null && (
                <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">GPU Memory</span>
                    <span className="font-medium text-gray-900">{sysMetrics.gpu_memory_percent?.toFixed(1)}%</span>
                  </div>
                  <ProgressBar value={sysMetrics.gpu_memory_percent} color="bg-teal-500" />
                </div>
              )}
            </div>
          )}
        </Section>

        {/* Workers & Model Serving */}
        <div className="grid grid-cols-2 gap-6">
          <Section title="Workers">
            {workers.length === 0 ? (
              <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-sm text-gray-400">
                No workers detected
              </div>
            ) : (
              <div className="space-y-2">
                {workers.map((w) => (
                  <div key={w.worker_id} className="bg-white rounded-xl border border-gray-200 p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`w-2.5 h-2.5 rounded-full ${w.status === "active" ? "bg-green-500" : "bg-gray-400"}`} />
                      <div>
                        <p className="text-sm font-medium text-gray-900">{w.worker_id}</p>
                        <p className="text-xs text-gray-400">{w.current_task ?? "idle"} &middot; {formatUptime(w.uptime_seconds)}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      <span>{w.cpu_percent?.toFixed(0)}% CPU</span>
                      <span>{w.memory_mb?.toFixed(0)} MB</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Section>

          <Section title="Model Serving">
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              {modelStats ? (
                <div className="space-y-3">
                  {Object.entries(modelStats).map(([key, val]) => (
                    <div key={key} className="flex items-center justify-between text-sm">
                      <span className="text-gray-500 capitalize">{key.replace(/_/g, " ")}</span>
                      <span className="font-medium text-gray-900">{String(val)}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-400 text-center py-4">No models loaded</p>
              )}
            </div>
          </Section>
        </div>

        {/* System Config */}
        {config && (
          <Section title="Configuration">
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-gray-400">Environment</span>
                  <p className="text-gray-900 font-medium">{String(config.app_env ?? "-")}</p>
                </div>
                <div>
                  <span className="text-gray-400">Version</span>
                  <p className="text-gray-900 font-medium">{String(config.version ?? "-")}</p>
                </div>
                <div>
                  <span className="text-gray-400">Services</span>
                  <p className="text-gray-900 font-medium">{config.services ? Object.keys(config.services).length : 0} registered</p>
                </div>
              </div>
              {config.features && (
                <div className="mt-4 pt-4 border-t border-gray-100">
                  <p className="text-xs text-gray-400 mb-2">Feature Flags</p>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(config.features as Record<string, boolean>).map(([flag, enabled]) => (
                      <span
                        key={flag}
                        className={`text-xs px-2 py-1 rounded-full ${enabled ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-400"}`}
                      >
                        {flag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </Section>
        )}

        {/* Recent Logs */}
        <Section title="Recent Logs">
          <div className="flex gap-2 mb-3">
            {["", "info", "warning", "error"].map((level) => (
              <button
                key={level}
                onClick={() => setLogLevel(level)}
                className={`px-3 py-1.5 text-sm rounded-lg border ${
                  logLevel === level
                    ? "bg-primary-50 border-primary-300 text-primary-700"
                    : "border-gray-200 text-gray-500 hover:bg-gray-50"
                }`}
              >
                {level || "All"}
              </button>
            ))}
            <input
              type="text"
              placeholder="Search logs..."
              value={logSearch}
              onChange={(e) => setLogSearch(e.target.value)}
              className="ml-auto rounded-lg border border-gray-300 px-3 py-1.5 text-sm w-64"
            />
          </div>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            {logsLoading ? (
              <div className="p-8 text-center text-sm text-gray-400">Loading logs...</div>
            ) : logs.length === 0 ? (
              <div className="p-8 text-center text-sm text-gray-400">No logs found</div>
            ) : (
              <div className="max-h-96 overflow-auto divide-y divide-gray-100">
                {logs.map((log, i) => (
                  <div key={i} className="px-4 py-3 flex items-start gap-3 text-sm hover:bg-gray-50">
                    <span className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${severityColor(log.severity)}`}>
                      {log.severity}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-gray-900 truncate">{log.message}</p>
                      <div className="flex gap-3 mt-0.5 text-xs text-gray-400">
                        <span>{log.component}</span>
                        <span>{new Date(log.timestamp).toLocaleTimeString()}</span>
                        {log.duration_ms != null && <span>{log.duration_ms?.toFixed(0)}ms</span>}
                        {log.trace_id && <span className="font-mono">{log.trace_id.slice(0, 8)}</span>}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Section>
      </main>
    </AuthGuard>
  );
}
