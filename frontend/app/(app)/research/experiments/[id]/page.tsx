"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowLeft, FlaskConical, GitBranch, Cpu, Database } from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
} from "recharts";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/ui/stat";
import { Spinner } from "@/components/ui/progress";

interface ExperimentDetail {
  id: string;
  name: string;
  description: string | null;
  version: number;
  seed: number;
  status: string;
  parameters: Record<string, unknown>;
  environment: Record<string, string>;
  dataset_id: string | null;
  model_id: string | null;
  result_summary: Record<string, unknown> | null;
  created_at: string | null;
  history: { version: number; status: string; created_at: string | null }[];
  benchmarks: { method: string; metrics: Record<string, number | string>; deleted_records: number; created_at: string | null }[];
}

const methodLabels: Record<string, string> = {
  original: "Original",
  full_retrain: "Full retrain",
  sisa: "SISA",
  influence: "Influence fn",
  certified: "Certified",
  veriunlearn: "VeriUnlearn",
};

const colors = ["#22d3ee", "#8b5cf6", "#34d399", "#f59e0b", "#f472b6", "#f87171", "#38bdf8", "#a3e635"];

export default function ExperimentDetailPage() {
  const { id } = useParams<{ id: string }>();

  const detail = useQuery<ExperimentDetail>({
    queryKey: ["experiment", id],
    queryFn: () => api.get(`/api/v1/experiments/${id}`),
    enabled: !!id,
  });

  if (detail.isLoading) {
    return <div className="flex justify-center py-20"><Spinner className="h-8 w-8" /></div>;
  }
  if (!detail.data) {
    return (
      <div className="flex flex-col items-center gap-3 py-20 text-slate-500">
        <FlaskConical className="h-10 w-10 text-slate-700" />
        <p className="text-sm">Experiment not found.</p>
        <Link href="/research/experiments"><span className="text-xs text-cyan-400">← back to experiments</span></Link>
      </div>
    );
  }

  const e = detail.data;
  const chartData = e.benchmarks.map((b) => ({
    name: methodLabels[b.method] ?? b.method,
    accuracy: +(Number(b.metrics.accuracy ?? 0) * 100).toFixed(1),
    f1: +Number(b.metrics.f1 ?? 0).toFixed(3),
    color: colors[e.benchmarks.indexOf(b) % colors.length],
  }));
  const best = [...e.benchmarks]
    .filter((b) => b.method !== "original")
    .sort((a, b) => Number(b.metrics.accuracy ?? 0) - Number(a.metrics.accuracy ?? 0))[0];

  return (
    <div className="space-y-6">
      <Link href="/research/experiments">
        <span className="flex items-center gap-1.5 text-xs text-slate-500 transition-colors hover:text-cyan-400">
          <ArrowLeft className="h-3.5 w-3.5" /> Experiments
        </span>
      </Link>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold tracking-tight">{e.name}</h1>
        <Badge tone="slate">v{e.version}</Badge>
        <Badge tone="cyan">seed {e.seed}</Badge>
        <Badge tone={e.status === "completed" ? "emerald" : e.status === "running" ? "amber" : "slate"}>{e.status}</Badge>
      </motion.div>

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Benchmark methods" value={e.benchmarks.length} icon={<FlaskConical className="h-4 w-4" />} accent="text-violet-400" />
        <StatCard
          label="Best unlearning"
          value={best ? methodLabels[best.method] ?? best.method : "—"}
          sub={best ? `acc ${(Number(best.metrics.accuracy) * 100).toFixed(1)}%` : undefined}
          icon={<GitBranch className="h-4 w-4" />}
          accent="text-emerald-400"
        />
        <StatCard label="Versions" value={e.history.length} icon={<GitBranch className="h-4 w-4" />} accent="text-cyan-400" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Benchmark accuracy by method</CardTitle></CardHeader>
          <CardContent>
            {e.benchmarks.length === 0 ? (
              <p className="py-10 text-center text-sm text-slate-500">No benchmark rows yet — run a benchmark with this experiment selected.</p>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={11} />
                  <YAxis stroke="#64748b" fontSize={11} />
                  <Tooltip contentStyle={{ background: "#0a0f1c", border: "1px solid #1e293b", borderRadius: 8 }} />
                  <Bar dataKey="accuracy" name="accuracy (%)" radius={[6, 6, 0, 0]}>
                    {chartData.map((d, i) => <Cell key={i} fill={d.color} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>
              <span className="flex items-center gap-2"><Cpu className="h-4 w-4 text-amber-400" /> Environment</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1.5">
              {Object.entries(e.environment ?? {}).map(([k, v]) => (
                <div key={k} className="flex items-center justify-between rounded-lg border border-slate-800/70 bg-slate-900/30 px-3 py-2 text-xs">
                  <span className="text-slate-400">{k}</span>
                  <span className="mono max-w-[60%] truncate text-slate-200">{v}</span>
                </div>
              ))}
              {(!e.environment || Object.keys(e.environment).length === 0) && (
                <p className="py-6 text-center text-sm text-slate-500">No environment captured yet.</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Parameters</CardTitle></CardHeader>
          <CardContent>
            <pre className="mono max-h-64 overflow-auto rounded-lg border border-slate-800 bg-slate-950/60 p-4 text-xs text-cyan-300">
              {JSON.stringify(e.parameters ?? {}, null, 2)}
            </pre>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>
              <span className="flex items-center gap-2"><Database className="h-4 w-4 text-cyan-400" /> Version history</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1.5">
              {[...(e.history ?? [])].reverse().map((h) => (
                <div key={h.version} className="flex items-center gap-3 rounded-lg border border-slate-800/70 bg-slate-900/30 px-3 py-2 text-xs">
                  <Badge tone="slate">v{h.version}</Badge>
                  <Badge tone={h.status === "completed" ? "emerald" : "amber"}>{h.status}</Badge>
                  <span className="ml-auto text-slate-500">{h.created_at ?? "—"}</span>
                </div>
              ))}
              {(!e.history || e.history.length === 0) && (
                <p className="py-6 text-center text-sm text-slate-500">Single version — use “Version” in the list to branch.</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {e.dataset_id && (
        <Card>
          <CardHeader><CardTitle>Result summary</CardTitle></CardHeader>
          <CardContent>
            <pre className="mono max-h-72 overflow-auto rounded-lg border border-slate-800 bg-slate-950/60 p-4 text-xs text-emerald-300">
              {JSON.stringify(e.result_summary ?? {}, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
