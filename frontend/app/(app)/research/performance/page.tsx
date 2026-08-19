"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Cpu, MemoryStick, HardDrive, Activity, RefreshCw } from "lucide-react";
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
import { StatCard } from "@/components/ui/stat";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/progress";

interface SystemMetrics {
  live: {
    ts: number;
    cpu_percent: number;
    ram_mb: number;
    system_cpu_percent: number;
    system_ram_mb: number;
    disk_used_mb: number;
  };
  series: Record<string, { value: number; unit: string; sampled_at: string | null }[]>;
}

export default function PerformancePage() {
  const metrics = useQuery<SystemMetrics>({
    queryKey: ["metrics-system"],
    queryFn: () => api.get("/api/v1/metrics/system"),
    refetchInterval: 8000,
  });

  const live = metrics.data?.live;
  const series = metrics.data?.series ?? {};

  const chartData = (series.system_cpu_percent ?? []).map((p, i) => ({
    i,
    cpu: +p.value.toFixed(1),
    ram: +((series.system_ram_mb ?? [])[i]?.value ?? 0).toFixed(0),
    disk: +((series.disk_used_mb ?? [])[i]?.value ?? 0).toFixed(0),
  }));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Performance Monitor</h1>
          <p className="mt-1 text-sm text-slate-500">
            Live resource sampling plus persisted time-series for CPU, RAM and disk — refreshed every 8s.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => metrics.refetch()} loading={metrics.isFetching}>
          <RefreshCw className="h-3.5 w-3.5" /> Refresh
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <StatCard
          label="Process CPU"
          value={live ? `${live.cpu_percent.toFixed(1)}%` : "—"}
          sub="worker process"
          icon={<Cpu className="h-4 w-4" />}
          accent="text-cyan-400"
          delay={0}
        />
        <StatCard
          label="System CPU"
          value={live ? `${live.system_cpu_percent.toFixed(1)}%` : "—"}
          sub="whole machine"
          icon={<Activity className="h-4 w-4" />}
          accent="text-violet-400"
          delay={0.05}
        />
        <StatCard
          label="Process RAM"
          value={live ? `${live.ram_mb.toFixed(0)} MB` : "—"}
          sub={`system ${live ? `${live.system_ram_mb.toFixed(0)} MB` : "—"}`}
          icon={<MemoryStick className="h-4 w-4" />}
          accent="text-emerald-400"
          delay={0.1}
        />
        <StatCard
          label="Disk used"
          value={live ? `${(live.disk_used_mb / 1024).toFixed(1)} GB` : "—"}
          sub="sampled on this host"
          icon={<HardDrive className="h-4 w-4" />}
          accent="text-amber-400"
          delay={0.15}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>
            <span className="flex items-center gap-2"><Activity className="h-4 w-4 text-cyan-400" /> System time-series</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {metrics.isLoading ? (
            <div className="flex justify-center py-10"><Spinner /></div>
          ) : chartData.length < 2 ? (
            <p className="py-10 text-center text-sm text-slate-500">
              Collecting samples — the chart appears after a few refresh cycles.
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="i" stroke="#64748b" fontSize={11} label={{ value: "sample #", position: "insideBottom", offset: -2, fill: "#64748b", fontSize: 10 }} />
                <YAxis yAxisId="cpu" stroke="#22d3ee" fontSize={11} unit="%" />
                <YAxis yAxisId="ram" orientation="right" stroke="#34d399" fontSize={11} unit=" MB" />
                <Tooltip contentStyle={{ background: "#0a0f1c", border: "1px solid #1e293b", borderRadius: 8 }} />
                <Legend />
                <Line yAxisId="cpu" type="monotone" dataKey="cpu" name="CPU %" stroke="#22d3ee" strokeWidth={2} dot={false} />
                <Line yAxisId="ram" type="monotone" dataKey="ram" name="RAM (MB)" stroke="#34d399" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Process vs system CPU</CardTitle></CardHeader>
          <CardContent>
            <p className="text-sm text-slate-400">
              The worker&apos;s CPU share versus total machine load. Spikes here indicate active training, embedding,
              or Merkle computation.
            </p>
            {chartData.length > 1 && (
              <div className="mt-4">
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="i" stroke="#64748b" fontSize={11} />
                    <YAxis stroke="#64748b" fontSize={11} unit="%" />
                    <Tooltip contentStyle={{ background: "#0a0f1c", border: "1px solid #1e293b", borderRadius: 8 }} />
                    <Legend />
                    <Line type="monotone" dataKey="cpu" name="CPU %" stroke="#22d3ee" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Sampled series</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2">
              {Object.entries(series).map(([key, samples]) => (
                <motion.div
                  key={key}
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="flex items-center justify-between rounded-lg border border-slate-800/70 bg-slate-900/30 px-3 py-2 text-xs"
                >
                  <span className="mono text-slate-400">{key}</span>
                  <span className="text-slate-300">
                    {samples.length} samples · latest{" "}
                    <span className="mono text-cyan-300">
                      {samples.length ? `${samples[samples.length - 1].value.toFixed(1)} ${samples[samples.length - 1].unit}` : "—"}
                    </span>
                  </span>
                </motion.div>
              ))}
              {Object.keys(series).length === 0 && (
                <p className="py-6 text-center text-sm text-slate-500">No samples persisted yet.</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
