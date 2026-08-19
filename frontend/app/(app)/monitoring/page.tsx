"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Activity, Cpu, MemoryStick, HardDrive, Database, Boxes, Timer, AlertTriangle, CheckCircle2, MinusCircle } from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/ui/stat";
import { Spinner } from "@/components/ui/progress";

interface Snapshot {
  ts: number;
  system: {
    cpu_percent: number;
    ram_mb: number;
    system_ram_mb: number;
    system_ram_used_mb: number;
    disk_used_mb: number;
    disk_total_mb: number;
  };
  dependencies: Record<string, { healthy: boolean | null; detail: Record<string, unknown> }>;
  queue: { in_flight: number; total: number };
  api: { uptime_seconds: number; avg_latency_ms: number | null; error_rate: number; requests_sampled: number };
}

interface HistoryRow {
  name: string;
  value: number;
  unit: string;
  healthy: boolean | null;
  sampled_at: string | null;
}

export default function MonitoringPage() {
  const data = useQuery<{ snapshot: Snapshot; history: HistoryRow[] }>({
    queryKey: ["monitoring-system"],
    queryFn: () => api.get("/api/v1/monitoring/system"),
    refetchInterval: 8000,
  });

  if (data.isLoading || !data.data) {
    return <div className="flex justify-center py-20"><Spinner className="h-8 w-8" /></div>;
  }

  const { snapshot, history } = data.data;
  const sys = snapshot.system;

  const cpuHistory = history.filter((h) => h.name === "cpu_percent").map((h, i) => ({ i, cpu: +h.value.toFixed(1) }));
  const ramHistory = history.filter((h) => h.name === "ram_mb").map((h, i) => ({ i, ram: +h.value.toFixed(0) }));
  const latencyHistory = history.filter((h) => h.name === "api.avg_latency_ms").map((h, i) => ({ i, latency: +h.value.toFixed(2) }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">System Monitoring</h1>
        <p className="mt-1 text-sm text-slate-500">
          Live resources, dependency health, worker queue, API latency/error rate — refreshed every 8s. Prometheus: <code className="mono rounded bg-slate-800 px-1 py-0.5 text-[11px]">/metrics</code>
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="CPU" value={`${sys.cpu_percent.toFixed(1)}%`} sub="process" icon={<Cpu className="h-4 w-4" />} accent="text-cyan-400" />
        <StatCard label="RAM" value={`${sys.ram_mb.toFixed(0)} MB`} sub={`system ${(sys.system_ram_used_mb / 1024).toFixed(1)} GB`} icon={<MemoryStick className="h-4 w-4" />} accent="text-violet-400" />
        <StatCard label="Disk" value={`${(sys.disk_used_mb / 1024 / 1024).toFixed(1)} GB`} sub={`of ${(sys.disk_total_mb / 1024 / 1024).toFixed(1)} GB`} icon={<HardDrive className="h-4 w-4" />} accent="text-amber-400" />
        <StatCard label="Uptime" value={`${(snapshot.api.uptime_seconds / 3600).toFixed(1)}h`} sub="since last deploy" icon={<Timer className="h-4 w-4" />} accent="text-emerald-400" />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* dependencies */}
        <Card>
          <CardHeader>
            <CardTitle>
              <span className="flex items-center gap-2"><Database className="h-4 w-4 text-cyan-400" /> Dependency health</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {Object.entries(snapshot.dependencies).map(([name, dep]) => (
              <motion.div
                key={name}
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex items-center gap-3 rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2.5"
              >
                {dep.healthy === true ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                ) : dep.healthy === false ? (
                  <AlertTriangle className="h-4 w-4 text-rose-400" />
                ) : (
                  <MinusCircle className="h-4 w-4 text-slate-500" />
                )}
                <span className="text-sm font-medium capitalize text-slate-200">{name}</span>
                <Badge tone={dep.healthy === true ? "emerald" : dep.healthy === false ? "rose" : "slate"} className="ml-auto">
                  {dep.healthy === true ? "healthy" : dep.healthy === false ? "down" : "optional"}
                </Badge>
              </motion.div>
            ))}
          </CardContent>
        </Card>

        {/* queue + api */}
        <Card>
          <CardHeader>
            <CardTitle>
              <span className="flex items-center gap-2"><Boxes className="h-4 w-4 text-violet-400" /> Worker queue & API</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-3">
                <p className="text-[10px] uppercase tracking-wider text-slate-500">Queue in flight</p>
                <p className="mono mt-1 text-2xl font-bold text-amber-300">{snapshot.queue.in_flight}</p>
                <p className="text-[10px] text-slate-500">of {snapshot.queue.total} total requests</p>
              </div>
              <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-3">
                <p className="text-[10px] uppercase tracking-wider text-slate-500">Error rate</p>
                <p className="mono mt-1 text-2xl font-bold text-rose-300">{(snapshot.api.error_rate * 100).toFixed(1)}%</p>
                <p className="text-[10px] text-slate-500">{snapshot.api.requests_sampled} requests sampled</p>
              </div>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-3">
              <p className="text-[10px] uppercase tracking-wider text-slate-500">Avg API latency</p>
              <p className="mono mt-1 text-2xl font-bold text-cyan-300">{snapshot.api.avg_latency_ms?.toFixed(1) ?? "—"} ms</p>
            </div>
          </CardContent>
        </Card>

        {/* prometheus */}
        <Card>
          <CardHeader>
            <CardTitle>
              <span className="flex items-center gap-2"><Activity className="h-4 w-4 text-emerald-400" /> Scrape targets</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-xs">
            <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-3">
              <p className="text-slate-400">Prometheus endpoint</p>
              <p className="mono mt-1 text-cyan-300">GET /metrics</p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-3">
              <p className="text-slate-400">Health check</p>
              <p className="mono mt-1 text-emerald-300">GET /health</p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-3">
              <p className="text-slate-400">Grafana dashboard</p>
              <p className="mono mt-1 text-violet-300">deploy/grafana/veriunlearn-dashboard.json</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>CPU & RAM history</CardTitle></CardHeader>
          <CardContent>
            {cpuHistory.length < 2 ? (
              <p className="py-10 text-center text-sm text-slate-500">Collecting samples…</p>
            ) : (
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={cpuHistory.map((c, i) => ({ i, cpu: c.cpu, ram: ramHistory[i]?.ram ?? 0 }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="i" stroke="#64748b" fontSize={11} />
                  <YAxis yAxisId="cpu" stroke="#22d3ee" fontSize={11} unit="%" />
                  <YAxis yAxisId="ram" orientation="right" stroke="#a78bfa" fontSize={11} unit=" MB" />
                  <Tooltip contentStyle={{ background: "#0a0f1c", border: "1px solid #1e293b", borderRadius: 8 }} />
                  <Legend />
                  <Line yAxisId="cpu" type="monotone" dataKey="cpu" name="CPU %" stroke="#22d3ee" strokeWidth={2} dot={false} />
                  <Line yAxisId="ram" type="monotone" dataKey="ram" name="RAM (MB)" stroke="#a78bfa" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>API latency history</CardTitle></CardHeader>
          <CardContent>
            {latencyHistory.length < 2 ? (
              <p className="py-10 text-center text-sm text-slate-500">Collecting samples…</p>
            ) : (
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={latencyHistory}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="i" stroke="#64748b" fontSize={11} />
                  <YAxis stroke="#64748b" fontSize={11} unit=" ms" />
                  <Tooltip contentStyle={{ background: "#0a0f1c", border: "1px solid #1e293b", borderRadius: 8 }} />
                  <Line type="monotone" dataKey="latency" name="avg latency (ms)" stroke="#34d399" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
