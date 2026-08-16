"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Gauge, Play } from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Table, THead, Th, Td, TRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

interface Dataset {
  id: string;
  name: string;
  record_count: number;
}

interface BenchRow {
  method: string;
  accuracy: number;
  f1: number;
  deletion_seconds: number;
  utility_loss: number;
  certified_bound?: number;
}

interface BenchResult {
  dataset_id: string;
  model_id: string;
  deleted_records: number;
  eval_records: number;
  results: BenchRow[];
  summary: string;
}

const methodLabels: Record<string, string> = {
  original: "Original model",
  sisa_retrain: "SISA retrain",
  certified_removal: "Certified removal",
  influence_scrub: "Influence scrub",
};

export default function BenchmarkPage() {
  const [datasetId, setDatasetId] = useState("");
  const [nDelete, setNDelete] = useState(50);
  const [notice, setNotice] = useState<string | null>(null);

  const { data: datasets } = useQuery<Dataset[]>({
    queryKey: ["datasets"],
    queryFn: () => api.get("/api/v1/datasets?limit=50"),
  });

  const run = useMutation({
    mutationFn: () =>
      api.post<BenchResult>(`/api/v1/benchmarks/run?dataset_id=${datasetId}&n_delete=${nDelete}`),
    onSuccess: () => setNotice(null),
    onError: (e) => setNotice(e instanceof ApiError ? e.message : "Benchmark failed"),
  });

  const chartData = (run.data?.results ?? []).map((r) => ({
    name: methodLabels[r.method] ?? r.method,
    accuracy: +(r.accuracy * 100).toFixed(1),
    "deletion (s)": +r.deletion_seconds.toFixed(3),
  }));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Benchmark</h1>
          <p className="mt-1 text-sm text-slate-500">
            Head-to-head: original vs SISA retrain vs certified removal vs influence scrub on the same holdout.
          </p>
        </div>
        <div className="flex items-end gap-3">
          <div>
            <label className="mb-1 block text-[11px] uppercase tracking-wider text-slate-500">Dataset</label>
            <Select value={datasetId} onChange={(e) => setDatasetId(e.target.value)} className="w-60">
              <option value="">Select…</option>
              {(datasets ?? []).map((d) => (
                <option key={d.id} value={d.id}>{d.name} ({d.record_count} rows)</option>
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
            <Play className="h-4 w-4" /> Run benchmark
          </Button>
        </div>
      </div>

      {notice && <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">{notice}</div>}

      {run.data && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Utility & cost comparison</CardTitle>
              <Badge tone="cyan">{run.data.deleted_records} records deleted · {run.data.eval_records} evaluated</Badge>
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

          <Card>
            <CardHeader>
              <CardTitle>Detailed results</CardTitle>
            </CardHeader>
            <Table>
              <THead>
                <tr>
                  <Th>Method</Th>
                  <Th>Accuracy</Th>
                  <Th>F1</Th>
                  <Th>Deletion time</Th>
                  <Th>Utility loss</Th>
                  <Th>Certified bound</Th>
                </tr>
              </THead>
              <tbody>
                {run.data.results.map((r) => (
                  <TRow key={r.method}>
                    <Td className="font-medium text-slate-100">{methodLabels[r.method] ?? r.method}</Td>
                    <Td className="mono">{(r.accuracy * 100).toFixed(1)}%</Td>
                    <Td className="mono">{r.f1.toFixed(3)}</Td>
                    <Td className="mono text-cyan-300">{r.deletion_seconds < 0.01 ? "<0.01s" : `${r.deletion_seconds.toFixed(3)}s`}</Td>
                    <Td className="mono">{r.utility_loss >= 0 ? `-${(r.utility_loss * 100).toFixed(2)}%` : "—"}</Td>
                    <Td className="mono text-xs text-violet-300">{r.certified_bound !== undefined ? r.certified_bound.toExponential(3) : "—"}</Td>
                  </TRow>
                ))}
              </tbody>
            </Table>
            <p className="mt-4 text-sm text-slate-500">{run.data.summary}</p>
          </Card>
        </>
      )}

      {!run.data && !run.isPending && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-slate-500">
            <Gauge className="h-10 w-10 text-slate-700" />
            <p className="text-sm">Run a benchmark to compare unlearning methods on a trained dataset.</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
