"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { FlaskConical, Plus, GitBranch, ArrowRight, Copy } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/ui/stat";
import { Select } from "@/components/ui/select";
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
  description: string | null;
  version: number;
  seed: number;
  status: string;
  result_summary: Record<string, unknown> | null;
  created_at: string | null;
}

export default function ExperimentsPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [seed, setSeed] = useState(42);
  const [datasetId, setDatasetId] = useState("");
  const [notice, setNotice] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  const experiments = useQuery<{ experiments: Experiment[] }>({
    queryKey: ["experiments"],
    queryFn: () => api.get("/api/v1/experiments"),
  });
  const datasets = useQuery<Dataset[]>({
    queryKey: ["datasets"],
    queryFn: () => api.get("/api/v1/datasets?limit=50"),
  });

  const create = useMutation({
    mutationFn: () =>
      api.post<Experiment>("/api/v1/experiments", {
        name,
        seed,
        dataset_id: datasetId || undefined,
        parameters: { n_delete: 50, eval_size: 300 },
      }),
    onSuccess: async (e) => {
      setNotice({ kind: "ok", text: `Experiment "${e.name}" v${e.version} created — run a benchmark against it.` });
      setName("");
      await qc.invalidateQueries({ queryKey: ["experiments"] });
    },
    onError: (e) => setNotice({ kind: "err", text: e instanceof ApiError ? e.message : "Creation failed" }),
  });

  const version = useMutation({
    mutationFn: (id: string) => api.post<{ id: string; version: number }>(`/api/v1/experiments/${id}/version`, {}),
    onSuccess: async () => {
      setNotice({ kind: "ok", text: "New experiment version created." });
      await qc.invalidateQueries({ queryKey: ["experiments"] });
    },
    onError: (e) => setNotice({ kind: "err", text: e instanceof ApiError ? e.message : "Versioning failed" }),
  });

  const exps = experiments.data?.experiments ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Experiment Manager</h1>
          <p className="mt-1 text-sm text-slate-500">
            Versioned, reproducible experiment runs — parameters, seeds, environments, and side-by-side results.
          </p>
        </div>
      </div>

      {notice && (
        <div
          className={`rounded-lg border px-4 py-3 text-sm ${
            notice.kind === "ok"
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
              : "border-rose-500/30 bg-rose-500/10 text-rose-300"
          }`}
        >
          {notice.text}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Experiments" value={exps.length} icon={<FlaskConical className="h-4 w-4" />} accent="text-violet-400" />
        <StatCard
          label="Completed"
          value={exps.filter((e) => e.status === "completed").length}
          icon={<GitBranch className="h-4 w-4" />}
          accent="text-emerald-400"
        />
        <StatCard
          label="Running"
          value={exps.filter((e) => e.status === "running").length}
          icon={<FlaskConical className="h-4 w-4" />}
          accent="text-amber-400"
        />
      </div>

      {/* create */}
      <Card>
        <CardHeader>
          <CardTitle>
            <span className="flex items-center gap-2"><Plus className="h-4 w-4 text-cyan-400" /> New experiment</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          <div className="flex-1">
            <label className="mb-1 block text-[11px] uppercase tracking-wider text-slate-500">Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. adult-census-v2-influence"
              className="w-full rounded-lg border border-slate-700 bg-slate-900/50 px-3 py-2 text-sm text-slate-200 outline-none focus:border-cyan-400/50"
            />
          </div>
          <div>
            <label className="mb-1 block text-[11px] uppercase tracking-wider text-slate-500">Seed</label>
            <input
              type="number"
              value={seed}
              onChange={(e) => setSeed(Number(e.target.value))}
              className="w-24 rounded-lg border border-slate-700 bg-slate-900/50 px-3 py-2 text-sm text-slate-200 outline-none focus:border-cyan-400/50"
            />
          </div>
          <div>
            <label className="mb-1 block text-[11px] uppercase tracking-wider text-slate-500">Dataset</label>
            <Select value={datasetId} onChange={(e) => setDatasetId(e.target.value)} className="w-56">
              <option value="">— optional —</option>
              {(datasets.data ?? []).map((d) => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </Select>
          </div>
          <Button disabled={!name.trim()} onClick={() => create.mutate()} loading={create.isPending}>
            <Plus className="h-4 w-4" /> Create
          </Button>
        </CardContent>
      </Card>

      {/* list */}
      <Card>
        <CardHeader>
          <CardTitle>Experiment history</CardTitle>
        </CardHeader>
        <CardContent>
          {experiments.isLoading ? (
            <div className="flex justify-center py-8"><Spinner /></div>
          ) : exps.length === 0 ? (
            <p className="py-8 text-center text-sm text-slate-500">No experiments yet — create one above.</p>
          ) : (
            <div className="space-y-2">
              {exps.map((e, i) => (
                <motion.div
                  key={e.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3"
                >
                  <span className={`h-2 w-2 rounded-full ${e.status === "completed" ? "bg-emerald-400" : e.status === "running" ? "bg-amber-400" : "bg-slate-600"}`} />
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-200">{e.name}</p>
                    {e.description && <p className="truncate text-xs text-slate-500">{e.description}</p>}
                  </div>
                  <Badge tone="slate">v{e.version}</Badge>
                  <Badge tone="cyan">seed {e.seed}</Badge>
                  <Badge tone={e.status === "completed" ? "emerald" : e.status === "running" ? "amber" : "slate"}>{e.status}</Badge>
                  <span className="mono hidden text-xs text-slate-500 lg:inline">
                    {e.result_summary && typeof e.result_summary === "object"
                      ? `benchmark methods: ${Object.keys(e.result_summary).length}`
                      : "no results yet"}
                  </span>
                  <span className="ml-auto text-xs text-slate-500">{timeAgo(e.created_at)}</span>
                  <Button variant="outline" size="sm" onClick={() => version.mutate(e.id)} disabled={version.isPending}>
                    <Copy className="h-3.5 w-3.5" /> Version
                  </Button>
                  <Link href={`/research/experiments/${e.id}`}>
                    <Button size="sm">Open <ArrowRight className="ml-1 h-3.5 w-3.5" /></Button>
                  </Link>
                </motion.div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
