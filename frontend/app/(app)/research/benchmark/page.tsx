"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Play, Download, BarChart3, History } from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
} from "recharts";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select } from "@/components/ui/select";
import { Table, THead, Th, Td, TRow } from "@/components/ui/table";
import { StatCard } from "@/components/ui/stat";
import { Spinner } from "@/components/ui/progress";
import { timeAgo } from "@/lib/utils";

interface Dataset {
  id: string;
  name: string;
  record_count: number;
}

interface Experiment {
  id: string;
  name: string;
}

interface BenchRow {
  method: string;
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  deletion_seconds: number;
  utility_loss: number;
  training_time_seconds: number;
  inference_latency_ms: number;
  forget_quality_score: number;
  privacy_gain: number;
  verification_seconds?: number;
}

interface BenchRunResult {
  experiment_id: string | null;
  dataset_id: string;
  model_id: string;
  deleted_records: number;
  seed: number;
  results: BenchRow[];
}

interface PersistedRow {
  id: string;
  experiment_id: string | null;
  dataset_id: string | null;
  model_id: string | null;
  method: string;
  deleted_records: number;
  eval_records: number;
  metrics: Record<string, number | string>;
  created_at: string | null;
}

const methodLabels: Record<string, string> = {
  original: "Original",
  full_retrain: "Full retrain",
  sisa: "SISA",
  influence: "Influence fn",
  certified: "Certified",
  veriunlearn: "VeriUnlearn",
};

const labelFor = (m: string) => methodLabels[m] ?? m;

export default function ResearchBenchmarkPage() {
  const qc = useQueryClient();
  const [datasetId, setDatasetId] = useState("");
  const [experimentId, setExperimentId] = useState("");
  const [nDelete, setNDelete] = useState(50);
  const [notice, setNotice] = useState<string | null>(null);

  const datasets = useQuery<Dataset[]>({
    queryKey: ["datasets"],
    queryFn: () => api.get("/api/v1/datasets?limit=50"),
  });
  const experiments = useQuery<{ experiments: Experiment[] }>({
    queryKey: ["experiments"],
    queryFn: () => api.get("/api/v1/experiments"),
  });
  const persisted = useQuery<{ results: PersistedRow[] }>({
    queryKey: ["benchmark-results"],
    queryFn: () => api.get("/api/v1/benchmark/results?limit=200"),
  });

  const run = useMutation({
    mutationFn: () =>
      api.post<BenchRunResult>("/api/v1/benchmark/run", {
        dataset_id: datasetId,
        n_delete: nDelete,
        experiment_id: experimentId || undefined,
      }),
    onSuccess: async () => {
      setNotice(null);
      await qc.invalidateQueries({ queryKey: ["benchmark-results"] });
      await qc.invalidateQueries({ queryKey: ["experiments"] });
      await qc.invalidateQueries({ queryKey: ["metrics-privacy"] });
    },
    onError: (e) => setNotice(e instanceof ApiError ? e.message : "Benchmark failed"),
  });

  const download = (format: "csv" | "json" | "xlsx") => {
    const url = `/api/v1/benchmark/export?format=${format}`;
    const a = document.createElement("a");
    a.href = url;
    a.download = `benchmark-results.${format}`;
    a.click();
  };

  const rows = useMemo(() => run.data?.results ?? [], [run.data]);
  const chartData = useMemo(
    () =>
      rows.map((r) => ({
        name: labelFor(r.method),
        accuracy: +(r.accuracy * 100).toFixed(1),
        "deletion (s)": +r.deletion_seconds.toFixed(2),
      })),
    [rows]
  );

  const radarData = useMemo(() => {
    const dims = [
      { key: "accuracy", label: "Accuracy", max: 1 },
      { key: "f1", label: "F1", max: 1 },
      { key: "forget_quality_score", label: "Forget quality", max: 1 },
      { key: "privacy_gain", label: "Privacy gain", max: 1 },
    ];
    return dims.map((d) => {
      const row: Record<string, number | string> = { dimension: d.label };
      for (const r of rows) {
        row[labelFor(r.method)] = +(Number(r[d.key as keyof BenchRow] ?? 0) / d.max).toFixed(3);
      }
      return row;
    });
  }, [rows]);

  const latest = persisted.data?.results ?? [];
  const avgDeletion = latest.length
    ? latest.reduce((a, r) => a + Number(r.metrics.deletion_seconds ?? 0), 0) / latest.length
    : 0;
  const bestRow = [...latest]
    .filter((r) => r.method !== "original" && typeof r.metrics.accuracy === "number")
    .sort((a, b) => Number(b.metrics.accuracy) - Number(a.metrics.accuracy))[0];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Benchmark Suite</h1>
          <p className="mt-1 text-sm text-slate-500">
            Six-method comparison — Original, Full Retrain, SISA, Influence, Certified, VeriUnlearn — on the same holdout.
          </p>
        </div>
        <div className="flex items-end gap-3">
          <div>
            <label className="mb-1 block text-[11px] uppercase tracking-wider text-slate-500">Dataset</label>
            <Select value={datasetId} onChange={(e) => setDatasetId(e.target.value)} className="w-56">
              <option value="">Select…</option>
              {(datasets.data ?? []).map((d) => (
                <option key={d.id} value={d.id}>{d.name} ({d.record_count} rows)</option>
              ))}
            </Select>
          </div>
          <div>
            <label className="mb-1 block text-[11px] uppercase tracking-wider text-slate-500">Experiment</label>
            <Select value={experimentId} onChange={(e) => setExperimentId(e.target.value)} className="w-44">
              <option value="">— none —</option>
              {(experiments.data?.experiments ?? []).map((e) => (
                <option key={e.id} value={e.id}>{e.name}</option>
              ))}
            </Select>
          </div>
          <div>
            <label className="mb-1 block text-[11px] uppercase tracking-wider text-slate-500">Records to delete</label>
            <Select value={nDelete} onChange={(e) => setNDelete(Number(e.target.value))} className="w-32">
              {[20, 50, 100, 200].map((n) => <option key={n} value={n}>{n}</option>)}
            </Select>
          </div>
          <Button disabled={!datasetId} onClick={() => run.mutate()} loading={run.isPending}>
            <Play className="h-4 w-4" /> Run
          </Button>
        </div>
      </div>

      {notice && <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">{notice}</div>}

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Benchmark rows stored" value={latest.length} icon={<BarChart3 className="h-4 w-4" />} accent="text-cyan-400" />
        <StatCard label="Avg deletion time" value={avgDeletion ? `${avgDeletion.toFixed(2)}s` : "—"} icon={<Play className="h-4 w-4" />} accent="text-violet-400" />
        <StatCard
          label="Best unlearning method"
          value={bestRow ? labelFor(bestRow.method) : "—"}
          sub={bestRow ? `acc ${(Number(bestRow.metrics.accuracy) * 100).toFixed(1)}%` : undefined}
          icon={<BarChart3 className="h-4 w-4" />}
          accent="text-emerald-400"
        />
      </div>

      {run.data && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Utility & cost comparison</CardTitle>
              <Badge tone="cyan">{run.data.deleted_records} records deleted · seed {run.data.seed}</Badge>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={11} />
                  <YAxis yAxisId="acc" stroke="#64748b" fontSize={11} />
                  <YAxis yAxisId="time" orientation="right" stroke="#8b5cf6" fontSize={11} />
                  <Tooltip contentStyle={{ background: "#0a0f1c", border: "1px solid #1e293b", borderRadius: 8 }} />
                  <Legend />
                  <Bar yAxisId="acc" dataKey="accuracy" name="accuracy (%)" fill="#22d3ee" radius={[5, 5, 0, 0]} />
                  <Bar yAxisId="time" dataKey="deletion (s)" name="deletion (s)" fill="#8b5cf6" radius={[5, 5, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader><CardTitle>Research metric radar</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={280}>
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="#1e293b" />
                    <PolarAngleAxis dataKey="dimension" stroke="#64748b" fontSize={11} />
                    <Radar name={labelFor(rows[0].method)} dataKey={labelFor(rows[0].method)} stroke="#22d3ee" fill="#22d3ee" fillOpacity={0.15} />
                    {rows.slice(1).map((r, i) => (
                      <Radar
                        key={r.method}
                        name={labelFor(r.method)}
                        dataKey={labelFor(r.method)}
                        stroke={["#8b5cf6", "#34d399", "#f59e0b", "#f472b6", "#f87171"][i % 5]}
                        fill="transparent"
                      />
                    ))}
                    <Tooltip contentStyle={{ background: "#0a0f1c", border: "1px solid #1e293b", borderRadius: 8 }} />
                    <Legend />
                  </RadarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Detailed results</CardTitle></CardHeader>
              <Table>
                <THead>
                  <tr>
                    <Th>Method</Th>
                    <Th>Acc</Th>
                    <Th>F1</Th>
                    <Th>Deletion</Th>
                    <Th>Utility loss</Th>
                    <Th>Forget quality</Th>
                  </tr>
                </THead>
                <tbody>
                  {rows.map((r) => (
                    <TRow key={r.method}>
                      <Td className="font-medium text-slate-100">{labelFor(r.method)}</Td>
                      <Td className="mono">{(r.accuracy * 100).toFixed(1)}%</Td>
                      <Td className="mono">{r.f1.toFixed(3)}</Td>
                      <Td className="mono text-cyan-300">{r.deletion_seconds < 0.01 ? "<0.01s" : `${r.deletion_seconds.toFixed(3)}s`}</Td>
                      <Td className="mono">{r.utility_loss >= 0 ? `-${(r.utility_loss * 100).toFixed(2)}%` : "—"}</Td>
                      <Td className="mono text-violet-300">{(r.forget_quality_score ?? 0).toFixed(3)}</Td>
                    </TRow>
                  ))}
                </tbody>
              </Table>
            </Card>
          </div>
        </>
      )}

      {/* persisted results + export */}
      <Card>
        <CardHeader>
          <CardTitle>
            <span className="flex items-center gap-2"><History className="h-4 w-4 text-violet-400" /> Persisted benchmark results</span>
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => download("csv")}><Download className="h-3.5 w-3.5" /> CSV</Button>
            <Button variant="outline" size="sm" onClick={() => download("json")}><Download className="h-3.5 w-3.5" /> JSON</Button>
            <Button variant="outline" size="sm" onClick={() => download("xlsx")}><Download className="h-3.5 w-3.5" /> Excel</Button>
          </div>
        </CardHeader>
        <CardContent>
          {persisted.isLoading ? (
            <div className="flex justify-center py-8"><Spinner /></div>
          ) : latest.length === 0 ? (
            <p className="py-8 text-center text-sm text-slate-500">No benchmark rows persisted yet — run one above.</p>
          ) : (
            <div className="max-h-96 space-y-1.5 overflow-auto">
              {latest.slice(0, 60).map((r, i) => (
                <motion.div
                  key={r.id}
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: Math.min(i * 0.02, 0.5) }}
                  className="flex flex-wrap items-center gap-2 rounded-lg border border-slate-800/70 bg-slate-900/30 px-3 py-2 text-xs"
                >
                  <Badge tone="violet">{labelFor(r.method)}</Badge>
                  <span className="mono text-slate-400">
                    acc {(Number(r.metrics.accuracy ?? 0) * 100).toFixed(1)}% · f1 {Number(r.metrics.f1 ?? 0).toFixed(2)} · del {Number(r.metrics.deletion_seconds ?? 0).toFixed(2)}s
                  </span>
                  <span className="mono hidden text-slate-600 md:inline">n={r.deleted_records} eval={r.eval_records}</span>
                  <span className="ml-auto text-slate-500">{timeAgo(r.created_at)}</span>
                </motion.div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
