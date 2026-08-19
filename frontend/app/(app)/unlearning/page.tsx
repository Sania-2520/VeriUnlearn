"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  Trash2,
  Scissors,
  Search,
  Activity,
  FileCheck2,
  Database,
  Layers,
  Cpu,
  Timer,
  ShieldAlert,
  ArrowRight,
  CheckCircle2,
  XCircle,
  Loader2,
  Eye,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress, Spinner } from "@/components/ui/progress";
import { Select } from "@/components/ui/select";
import { shortHash, formatSeconds } from "@/lib/utils";

interface ImpactReport {
  scope: string;
  totals: {
    records: number;
    embeddings: number;
    vectors: number;
    knowledge_chunks: number;
    affected_shards: number;
    influence_abs_sum: number;
  };
  datasets: Record<
    string,
    {
      dataset_id: string;
      dataset_name: string;
      dataset_version: number;
      record_count: number;
      record_ids: string[];
      embedding_ids: (string | number | null)[];
      vector_ids: (string | number | null)[];
      knowledge_chunks: string[];
      chat_ids: string[];
      affected_shards: number[];
      influence: { mean: number | null; abs_sum: number };
      dependencies: { model_id: string | null; model_version: number | null; adapters: string[] };
      estimated_retraining_seconds: number;
      deletion_eligible: boolean;
    }
  >;
  eligible: boolean;
}

interface RequestOut {
  id: string;
  status: string;
  error: string | null;
  certificate_id: string | null;
  result: Record<string, unknown>;
  duration_seconds: number | null;
}

interface Match {
  record_id: string;
  identity_key: string;
  full_name: string;
  email: string;
  chat_id: string | null;
  confidence: number;
  source: string;
  shard_id: number;
  sensitivity: string;
  influence_score: number | null;
}

const STEPS = [
  { key: "tombstone", label: "Tombstone records" },
  { key: "embedding", label: "Remove embeddings" },
  { key: "retrain", label: "Retrain affected shards" },
  { key: "root", label: "Recompute Merkle roots" },
  { key: "sign", label: "Sign certificate" },
];

export default function UnlearningPage() {
  const qc = useQueryClient();
  const [scope, setScope] = useState<"records" | "chat" | "dataset">("records");
  const [query, setQuery] = useState("");
  const [chatId, setChatId] = useState("");
  const [datasetSelection, setDatasetSelection] = useState("");
  const [method, setMethod] = useState("retrain");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [impact, setImpact] = useState<ImpactReport | null>(null);
  const [activeRequest, setActiveRequest] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  // ---- identity search for record selection ----
  const search = useMutation({
    mutationFn: (q: string) =>
      api.post<{ matches: Match[] }>(`/api/v1/privacy/search?query=${encodeURIComponent(q)}&limit=100`),
    onError: (e) => setNotice({ kind: "err", text: e instanceof ApiError ? e.message : "Search failed" }),
  });

  // ---- impact analysis ----
  const impactMutation = useMutation({
    mutationFn: () =>
      api.post<ImpactReport>("/api/v1/unlearning/impact", {
        scope,
        identity_key: scope === "records" && query ? query : undefined,
        record_ids: scope === "records" ? selectedIds : undefined,
        chat_id: scope === "chat" ? chatId : undefined,
        dataset_id: scope === "dataset" ? datasetSelection : undefined,
      }),
    onSuccess: (data) => {
      setImpact(data);
      setNotice(null);
    },
    onError: (e) => setNotice({ kind: "err", text: e instanceof ApiError ? e.message : "Impact analysis failed" }),
  });

  // ---- deletion execution ----
  const deleteMutation = useMutation({
    mutationFn: () =>
      api.post<RequestOut>("/api/v1/unlearning/selective", {
        scope,
        method,
        deletion_type: scope === "chat" ? "chat" : scope === "dataset" ? "dataset" : "records",
        identity_key: scope === "records" && query ? query : undefined,
        record_ids: scope === "records" ? selectedIds : undefined,
        chat_id: scope === "chat" ? chatId : undefined,
        dataset_id: scope === "dataset" ? datasetSelection : undefined,
      }),
    onSuccess: (data) => {
      setActiveRequest(data.id);
      setNotice(null);
      qc.invalidateQueries({ queryKey: ["datasets"] });
    },
    onError: (e) => setNotice({ kind: "err", text: e instanceof ApiError ? e.message : "Deletion failed" }),
  });

  // ---- poll request status ----
  const request = useQuery<RequestOut>({
    queryKey: ["unlearning-request", activeRequest],
    queryFn: () => api.get(`/api/v1/unlearning/requests/${activeRequest}`),
    enabled: !!activeRequest,
    refetchInterval: (q) =>
      q.state.data?.status === "completed" || q.state.data?.status === "failed" ? false : 1200,
  });

  const done = request.data?.status === "completed";
  const failed = request.data?.status === "failed";

  const runImpact = () => {
    if (scope === "records" && selectedIds.length === 0) {
      setNotice({ kind: "err", text: "Select at least one record (or use identity search)." });
      return;
    }
    if (scope === "chat" && !chatId) {
      setNotice({ kind: "err", text: "Enter a chat ID." });
      return;
    }
    if (scope === "dataset" && !datasetSelection) {
      setNotice({ kind: "err", text: "Pick a dataset." });
      return;
    }
    impactMutation.mutate();
  };

  const toggleRecord = (id: string) =>
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));

  const datasetEntries = impact
    ? Object.values(impact.datasets)
    : [];

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold tracking-tight">Surgical Machine Unlearning</h1>
        <p className="mt-1 text-sm text-slate-500">
          Select records → impact analysis → embedding removal + SISA shard retraining → verified deletion report.
        </p>
      </motion.div>

      {notice && (
        <div
          className={`flex items-start gap-2 rounded-lg border px-4 py-3 text-sm ${
            notice.kind === "ok"
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
              : "border-rose-500/30 bg-rose-500/10 text-rose-200"
          }`}
        >
          {notice.kind === "ok" ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> : <XCircle className="mt-0.5 h-4 w-4 shrink-0" />}
          {notice.text}
        </div>
      )}

      {/* STEP 1 — selection */}
      <Card>
        <CardHeader>
          <CardTitle>
            <span className="flex items-center gap-2"><Scissors className="h-4 w-4 text-cyan-400" /> Step 1 · Record selection</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-sm text-slate-400">Scope:</span>
            <div className="flex gap-2">
              {([
                ["records", "Records / identity"],
                ["chat", "Entire conversation"],
                ["dataset", "Entire dataset"],
              ] as const).map(([value, label]) => (
                <button
                  key={value}
                  onClick={() => {
                    setScope(value);
                    setImpact(null);
                  }}
                  className={`rounded-lg border px-3 py-2 text-sm transition-colors ${
                    scope === value
                      ? "border-cyan-400/50 bg-cyan-500/10 text-cyan-300"
                      : "border-slate-700 text-slate-400 hover:bg-slate-800/50"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {scope === "records" && (
            <div className="space-y-3">
              <div className="flex gap-3">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                  <Input
                    className="pl-9"
                    placeholder="Search identity by name / email / phone / Aadhaar / PAN…"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && search.mutate(query)}
                  />
                </div>
                <Button variant="outline" onClick={() => search.mutate(query)} loading={search.isPending}>
                  Search
                </Button>
              </div>

              {search.data && search.data.matches.length > 0 && (
                <div className="max-h-64 overflow-auto rounded-xl border border-slate-800">
                  <table className="w-full text-sm">
                    <thead className="sticky top-0 bg-slate-900 text-left text-[11px] uppercase tracking-wider text-slate-500">
                      <tr>
                        <th className="px-3 py-2">✓</th>
                        <th className="px-3 py-2">Identity</th>
                        <th className="px-3 py-2">Confidence</th>
                        <th className="px-3 py-2">Source</th>
                        <th className="px-3 py-2">Chat</th>
                        <th className="px-3 py-2">Shard</th>
                        <th className="px-3 py-2"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {search.data.matches.map((m) => (
                        <tr key={m.record_id} className="border-t border-slate-800/60 hover:bg-slate-900/40">
                          <td className="px-3 py-2">
                            <input
                              type="checkbox"
                              checked={selectedIds.includes(m.record_id)}
                              onChange={() => toggleRecord(m.record_id)}
                              className="accent-cyan-400"
                            />
                          </td>
                          <td className="px-3 py-2">
                            <span className="font-medium text-slate-200">{m.full_name}</span>
                            <span className="mono block text-xs text-slate-500">{m.email}</span>
                          </td>
                          <td className="px-3 py-2 text-xs text-emerald-300">{(m.confidence * 100).toFixed(0)}%</td>
                          <td className="px-3 py-2 text-xs text-slate-400">{m.source}</td>
                          <td className="mono px-3 py-2 text-xs text-slate-500">{m.chat_id ?? "—"}</td>
                          <td className="mono px-3 py-2 text-xs">{m.shard_id}</td>
                          <td className="px-3 py-2">
                            <Link href={`/privacy/records?id=${m.record_id}`} target="_blank">
                              <Button variant="ghost" size="sm">
                                <Eye className="h-3.5 w-3.5" />
                              </Button>
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <p className="text-xs text-slate-500">{selectedIds.length} record(s) selected.</p>
            </div>
          )}

          {scope === "chat" && (
            <div className="flex gap-3">
              <Input placeholder="chat id — e.g. chat-3" value={chatId} onChange={(e) => setChatId(e.target.value)} className="max-w-sm" />
            </div>
          )}

          {scope === "dataset" && (
            <DatasetPicker value={datasetSelection} onChange={setDatasetSelection} />
          )}

          <div className="flex flex-wrap items-center gap-3 border-t border-slate-800/70 pt-4">
            <div className="mr-auto flex items-center gap-2 text-sm text-slate-400">
              <span>Method:</span>
              <Select value={method} onChange={(e) => setMethod(e.target.value)} className="w-48">
                <option value="retrain">SISA shard retrain</option>
                <option value="certified">Certified Newton removal</option>
                <option value="influence">Influence gradient scrub</option>
              </Select>
            </div>
            <Button onClick={runImpact} loading={impactMutation.isPending} disabled={deleteMutation.isPending}>
              <Activity className="h-4 w-4" /> Impact analysis
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* STEP 2 — impact report */}
      <AnimatePresence>
        {impact && (
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 16 }}>
            <Card className="border-violet-500/30">
              <CardHeader>
                <CardTitle>
                  <span className="flex items-center gap-2">
                    <ShieldAlert className="h-4 w-4 text-violet-400" /> Step 2 · Impact analysis
                    {impact.eligible ? <Badge tone="emerald">eligible</Badge> : <Badge tone="rose">model required</Badge>}
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
                  {[
                    { icon: Database, label: "Records", value: impact.totals.records },
                    { icon: Layers, label: "Embeddings", value: impact.totals.embeddings },
                    { icon: Layers, label: "Chunks", value: impact.totals.knowledge_chunks },
                    { icon: Cpu, label: "Shards", value: impact.totals.affected_shards },
                    { icon: Activity, label: "Σ|influence|", value: impact.totals.influence_abs_sum.toFixed(3) },
                  ].map((s) => (
                    <div key={s.label} className="rounded-xl border border-slate-800 bg-slate-900/50 p-3">
                      <s.icon className="mb-2 h-4 w-4 text-violet-400" />
                      <p className="text-[10px] uppercase tracking-wider text-slate-500">{s.label}</p>
                      <p className="mt-0.5 text-lg font-bold text-slate-100">{s.value}</p>
                    </div>
                  ))}
                </div>

                <div className="space-y-3">
                  {datasetEntries.map((d) => (
                    <div key={d.dataset_id} className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-slate-200">{d.dataset_name}</span>
                        <Badge tone="cyan" className="mono">v{d.dataset_version}</Badge>
                        <span className="ml-auto text-xs text-slate-500">
                          est. retrain <span className="text-slate-300">{formatSeconds(d.estimated_retraining_seconds)}</span>
                        </span>
                      </div>
                      <div className="mt-3 grid gap-2 text-xs sm:grid-cols-2 lg:grid-cols-4">
                        <div className="rounded-lg bg-slate-950/50 px-3 py-2">
                          <p className="text-slate-500">records</p>
                          <p className="mt-0.5 font-semibold text-slate-200">{d.record_count}</p>
                        </div>
                        <div className="rounded-lg bg-slate-950/50 px-3 py-2">
                          <p className="text-slate-500">shards</p>
                          <p className="mono mt-0.5 font-semibold text-slate-200">{d.affected_shards.join(", ")}</p>
                        </div>
                        <div className="rounded-lg bg-slate-950/50 px-3 py-2">
                          <p className="text-slate-500">influence μ</p>
                          <p className="mono mt-0.5 font-semibold text-slate-200">
                            {d.influence.mean !== null ? d.influence.mean.toFixed(5) : "—"}
                          </p>
                        </div>
                        <div className="rounded-lg bg-slate-950/50 px-3 py-2">
                          <p className="text-slate-500">model</p>
                          <p className="mono mt-0.5 font-semibold text-slate-200">
                            {d.dependencies.model_id ? `v${d.dependencies.model_version}` : "—"}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="flex items-center gap-3 border-t border-slate-800/70 pt-4">
                  <Button
                    variant="danger"
                    onClick={() => deleteMutation.mutate()}
                    loading={deleteMutation.isPending}
                    disabled={!impact.eligible}
                  >
                    <Trash2 className="h-4 w-4" /> Delete {impact.totals.records} record(s) & unlearn
                  </Button>
                  <span className="text-xs text-slate-500">
                    Only the {impact.totals.affected_shards} affected shard(s) retrain — unrelated knowledge is untouched.
                  </span>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* STEP 3–7 — pipeline monitor + deletion report */}
      {activeRequest && (
        <Card className="border-emerald-500/30">
          <CardHeader>
            <CardTitle>
              <span className="flex items-center gap-2">
                <Timer className="h-4 w-4 text-emerald-400" /> Deletion pipeline
                {request.data?.id && <span className="mono text-sm text-slate-500">{shortHash(request.data.id, 12)}</span>}
              </span>
            </CardTitle>
            <Badge tone={done ? "emerald" : failed ? "rose" : "amber"}>{request.data?.status ?? "queued"}</Badge>
          </CardHeader>
          <CardContent>
            {!done && !failed && (
              <div className="space-y-4">
                <Progress value={request.data ? 72 : 25} className="mb-2" />
                <AnimatedTimeline active={request.data ? 4 : 2} />
                <p className="flex items-center gap-2 text-sm text-slate-400">
                  <Loader2 className="h-4 w-4 animate-spin text-cyan-400" />
                  {request.data?.status === "in_progress"
                    ? "Scrubbing shards, recomputing Merkle roots, signing certificate…"
                    : "Queued — worker picking up the request…"}
                </p>
              </div>
            )}

            {done && request.data && <DeletionReport request={request.data} />}

            {failed && (
              <div className="flex items-start gap-2 rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                <XCircle className="mt-0.5 h-4 w-4 shrink-0" />
                {request.data?.error ?? "Deletion failed."}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function AnimatedTimeline({ active }: { active: number }) {
  return (
    <div className="flex items-center gap-1">
      {STEPS.map((s, i) => (
        <div key={s.key} className="flex flex-1 flex-col items-center gap-1.5">
          <div
            className={`h-2 w-full rounded-full transition-colors ${
              i < active ? "bg-emerald-400" : i === active ? "animate-pulse bg-cyan-400" : "bg-slate-800"
            }`}
          />
          <span className={`text-[10px] ${i <= active ? "text-slate-300" : "text-slate-600"}`}>{s.label}</span>
        </div>
      ))}
    </div>
  );
}

function DeletionReport({ request }: { request: RequestOut }) {
  const result = (request.result ?? {}) as Record<string, unknown> & {
    deleted_records?: number;
    model_version?: number;
  };
  const datasets = (result.datasets as string[] | undefined) ?? [];
  const certId = request.certificate_id;

  return (
    <div className="space-y-4">
      <div className="flex items-start gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-200">
        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
        Deletion completed in {formatSeconds(request.duration_seconds)} — records tombstoned, embeddings removed,
        affected shards retrained, Merkle roots recomputed.
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
          <p className="text-[10px] uppercase tracking-wider text-slate-500">Records deleted</p>
          <p className="mt-1 text-2xl font-bold text-rose-300">{result.deleted_records ?? "—"}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
          <p className="text-[10px] uppercase tracking-wider text-slate-500">Datasets affected</p>
          <p className="mt-1 text-2xl font-bold text-slate-100">{datasets.length}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
          <p className="text-[10px] uppercase tracking-wider text-slate-500">Model version</p>
          <p className="mt-1 text-2xl font-bold text-slate-100">{result.model_version ?? "—"}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
          <p className="text-[10px] uppercase tracking-wider text-slate-500">Status</p>
          <p className="mt-1 text-2xl font-bold text-emerald-300">verified</p>
        </div>
      </div>

      {/* before / after comparison */}
      {datasets.map((dsId) => {
        const entry = (result as Record<string, unknown>)[dsId] as
          | { before?: { records: number; embeddings: number }; after?: { records: number; embeddings: number }; vectors_removed?: number; shards?: number[] }
          | undefined;
        if (!entry?.before || !entry?.after) return null;
        const b = entry.before;
        const a = entry.after;
        return (
          <div key={dsId} className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
            <p className="mono mb-3 text-xs text-slate-500">dataset {shortHash(dsId, 10)}</p>
            <div className="grid gap-3 sm:grid-cols-3">
              <CompareCell label="Records" before={b.records} after={a.records} />
              <CompareCell label="Embeddings" before={b.embeddings} after={a.embeddings} />
              <div className="rounded-lg bg-slate-950/50 p-3">
                <p className="text-[10px] uppercase tracking-wider text-slate-500">Vectors removed</p>
                <p className="mt-1 text-xl font-bold text-rose-300">{entry.vectors_removed ?? "—"}</p>
                <p className="text-xs text-slate-500">shards {entry.shards?.join(", ") ?? "—"}</p>
              </div>
            </div>
          </div>
        );
      })}

      {certId && (
        <div className="flex flex-wrap items-center gap-3 border-t border-slate-800/70 pt-4">
          <Link href={`/certificates/${certId}`}>
            <Button>
              <FileCheck2 className="h-4 w-4" /> View deletion certificate
            </Button>
          </Link>
          <span className="mono text-xs text-slate-500">{shortHash(certId, 18)}</span>
        </div>
      )}
    </div>
  );
}

function CompareCell({ label, before, after }: { label: string; before: number; after: number }) {
  const delta = before - after;
  return (
    <div className="rounded-lg bg-slate-950/50 p-3">
      <p className="text-[10px] uppercase tracking-wider text-slate-500">{label}</p>
      <div className="mt-1 flex items-center gap-2">
        <span className="text-lg font-bold text-slate-300">{before}</span>
        <ArrowRight className="h-4 w-4 text-slate-600" />
        <span className="text-lg font-bold text-emerald-300">{after}</span>
        <span className="ml-auto text-xs text-rose-300">−{delta}</span>
      </div>
    </div>
  );
}

function DatasetPicker({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const datasets = useQuery<{ datasets: { id: string; name: string; record_count: number; status: string }[] }>({
    queryKey: ["datasets"],
    queryFn: () => api.get("/api/v1/datasets"),
  });
  if (datasets.isLoading) return <Spinner />;
  const list = datasets.data?.datasets ?? [];
  return (
    <div className="max-h-64 space-y-2 overflow-auto">
      {list.length === 0 && <p className="text-sm text-slate-500">No datasets uploaded yet.</p>}
      {list.map((d) => (
        <label
          key={d.id}
          className={`flex cursor-pointer items-center gap-3 rounded-lg border px-3 py-2.5 text-sm transition-colors ${
            value === d.id ? "border-cyan-400/50 bg-cyan-500/10" : "border-slate-800 hover:bg-slate-900/40"
          }`}
        >
          <input type="radio" name="dataset" checked={value === d.id} onChange={() => onChange(d.id)} className="accent-cyan-400" />
          <Database className="h-4 w-4 text-slate-500" />
          <span className="font-medium text-slate-200">{d.name}</span>
          <span className="ml-auto text-xs text-slate-500">{d.record_count} records · {d.status}</span>
        </label>
      ))}
    </div>
  );
}
