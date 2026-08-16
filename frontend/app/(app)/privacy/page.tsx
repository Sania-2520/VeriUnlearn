"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  Fingerprint,
  Search,
  ShieldAlert,
  Trash2,
  Eye,
  FileCheck2,
  Layers,
  Braces,
  Cpu,
  Database,
  BadgeCheck,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress, Spinner } from "@/components/ui/progress";
import { Table, THead, Th, Td, TRow } from "@/components/ui/table";
import { Select } from "@/components/ui/select";
import { shortHash } from "@/lib/utils";

interface Match {
  record_id: string;
  identity_key: string;
  full_name: string;
  email: string;
  confidence: number;
  source: string;
  dataset_id: string;
  model_id: string | null;
  model_version: number | null;
  shard_id: number;
  sensitivity: string;
  influence_score: number | null;
  has_embedding: boolean;
  adapter: string | null;
  is_deleted: boolean;
}

type Footprint = {
  identity_key: string;
  full_name: string;
  email: string;
  total_records: number;
  active_records: number;
  deleted_records: number;
  record_ids: string[];
  embedding_ids: string[];
  knowledge_clusters: { dataset: string; shard_id: number; record_count: number; model_id: string | null }[];
  affected_neurons: { feature: string; weight: number }[];
  adapters: string[];
  data_importance: { mean_influence: number | null; max_influence: number | null };
  sensitivity: string[];
};

type RequestOut = {
  id: string;
  status: string;
  certificate_id: string | null;
  result: Record<string, unknown>;
  error: string | null;
};

export default function PrivacyPage() {
  const qc = useQueryClient();
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Match | null>(null);
  const [method, setMethod] = useState("retrain");
  const [activeRequest, setActiveRequest] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const search = useMutation({
    mutationFn: (q: string) => api.post<{ matches: Match[] }>(`/api/v1/privacy/search?query=${encodeURIComponent(q)}`),
    onError: (e) => setNotice(e instanceof ApiError ? e.message : "Search failed"),
  });

  const footprint = useQuery<Footprint>({
    queryKey: ["footprint", selected?.identity_key],
    queryFn: () => api.get(`/api/v1/privacy/footprint/${selected!.identity_key}`),
    enabled: !!selected,
  });

  const request = useQuery<RequestOut>({
    queryKey: ["unlearning-request", activeRequest],
    queryFn: () => api.get(`/api/v1/unlearning/requests/${activeRequest}`),
    enabled: !!activeRequest,
    refetchInterval: (q) => (q.state.data?.status === "completed" || q.state.data?.status === "failed" ? false : 1500),
  });

  const deleteSelected = useMutation({
    mutationFn: () =>
      api.post<RequestOut>("/api/v1/unlearning/selective", {
        identity_key: selected!.identity_key,
        deletion_type: "records",
        method,
      }),
    onSuccess: (data) => {
      setActiveRequest(data.id);
      setNotice(null);
    },
    onError: (e) => setNotice(e instanceof ApiError ? e.message : "Deletion failed"),
  });

  const fullReset = useMutation({
    mutationFn: () =>
      api.post<RequestOut>("/api/v1/unlearning/full-reset", { identity_key: selected!.identity_key }),
    onSuccess: (data) => {
      setActiveRequest(data.id);
      setNotice(null);
    },
    onError: (e) => setNotice(e instanceof ApiError ? e.message : "Reset failed"),
  });

  const verify = useMutation({
    mutationFn: (certId: string) => api.post<{ verified: boolean }>(`/api/v1/verification/verify/${certId}`),
    onSuccess: async (data) => {
      setNotice(data.verified ? "✅ Certificate verified — signature, hashes and Merkle roots all check out." : "❌ Verification failed — certificate integrity is broken.");
      await qc.invalidateQueries({ queryKey: ["certificates"] });
    },
    onError: (e) => setNotice(e instanceof ApiError ? e.message : "Verification failed"),
  });

  const done = request.data?.status === "completed";
  const failed = request.data?.status === "failed";

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold tracking-tight">Privacy Auditor</h1>
        <p className="mt-1 text-sm text-slate-500">
          Scan every model shard for an identity — then surgically remove it and mint a verifiable deletion certificate.
        </p>
      </motion.div>

      {notice && (
        <div className="flex items-start gap-2 rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-4 py-3 text-sm text-cyan-200">
          <BadgeCheck className="mt-0.5 h-4 w-4 shrink-0" /> {notice}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Identity Search</CardTitle>
          <Fingerprint className="h-5 w-5 text-cyan-400" />
        </CardHeader>
        <CardContent>
          <div className="flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
              <Input
                className="pl-9"
                placeholder="Search a name or email — e.g. 'maya' or 'nguyen'"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && search.mutate(query)}
              />
            </div>
            <Button onClick={() => search.mutate(query)} loading={search.isPending}>
              Audit all shards
            </Button>
          </div>
        </CardContent>
      </Card>

      {search.data && (
        <Card>
          <CardHeader>
            <CardTitle>
              {search.data.matches.length} match{search.data.matches.length === 1 ? "" : "es"} across all shards
            </CardTitle>
            <Badge tone="cyan">full-shard scan</Badge>
          </CardHeader>
          <Table>
            <THead>
              <tr>
                <Th>Identity</Th>
                <Th>Confidence</Th>
                <Th>Source / Model</Th>
                <Th>Shard</Th>
                <Th>Sensitivity</Th>
                <Th>Influence</Th>
                <Th>Embedding</Th>
                <Th>Adapter</Th>
                <Th></Th>
              </tr>
            </THead>
            <tbody>
              {search.data.matches.map((m) => (
                <TRow key={m.record_id}>
                  <Td>
                    <div className="font-medium text-slate-100">{m.full_name}</div>
                    <div className="mono text-xs text-slate-500">{m.email}</div>
                  </Td>
                  <Td>
                    <span className={m.confidence > 0.8 ? "font-semibold text-emerald-300" : "text-amber-300"}>
                      {(m.confidence * 100).toFixed(1)}%
                    </span>
                  </Td>
                  <Td>
                    <div>{m.source}</div>
                    {m.model_id && <div className="mono text-xs text-slate-500">model v{m.model_version}</div>}
                  </Td>
                  <Td className="mono">{m.shard_id}</Td>
                  <Td>
                    <Badge tone={m.sensitivity === "sensitive" ? "rose" : "amber"}>{m.sensitivity}</Badge>
                  </Td>
                  <Td className="mono text-xs">{m.influence_score !== null ? m.influence_score.toFixed(4) : "—"}</Td>
                  <Td>{m.has_embedding ? <Badge tone="emerald">indexed</Badge> : <span className="text-slate-600">—</span>}</Td>
                  <Td className="mono text-xs">{m.adapter ?? "—"}</Td>
                  <Td>
                    <Button variant="outline" size="sm" onClick={() => setSelected(m)}>
                      <Eye className="h-3.5 w-3.5" /> Footprint
                    </Button>
                  </Td>
                </TRow>
              ))}
            </tbody>
          </Table>
        </Card>
      )}

      <AnimatePresence>
        {selected && (
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 16 }}>
            <Card className="border-cyan-500/30">
              <CardHeader>
                <CardTitle>Identity Footprint — {selected.full_name}</CardTitle>
                <Badge tone="cyan" className="mono">{selected.identity_key}</Badge>
              </CardHeader>

              {footprint.isLoading ? (
                <div className="flex justify-center py-8"><Spinner /></div>
              ) : footprint.data ? (
                <CardContent>
                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                    {[
                      { icon: Database, label: "Records", value: `${footprint.data.active_records} active / ${footprint.data.deleted_records} deleted` },
                      { icon: Layers, label: "Knowledge clusters", value: footprint.data.knowledge_clusters.length },
                      { icon: Braces, label: "Embeddings", value: footprint.data.embedding_ids.length },
                      {
                        icon: ShieldAlert,
                        label: "Data importance",
                        value: footprint.data.data_importance.mean_influence !== null
                          ? `μ ${footprint.data.data_importance.mean_influence.toFixed(4)}`
                          : "not scored",
                      },
                    ].map((s) => (
                      <div key={s.label} className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
                        <s.icon className="mb-2 h-5 w-5 text-cyan-400" />
                        <p className="text-[11px] uppercase tracking-wider text-slate-500">{s.label}</p>
                        <p className="mt-1 text-sm font-medium text-slate-100">{s.value}</p>
                      </div>
                    ))}
                  </div>

                  <div className="mt-5 grid gap-5 lg:grid-cols-2">
                    <div>
                      <p className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-300">
                        <Layers className="h-4 w-4 text-cyan-400" /> Knowledge clusters
                      </p>
                      <div className="space-y-2">
                        {footprint.data.knowledge_clusters.map((c, i) => (
                          <div key={i} className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2 text-sm">
                            <span className="text-slate-300">{c.dataset}</span>
                            <span className="mono text-xs text-slate-500">shard {c.shard_id} · {c.record_count} records</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-300">
                        <Cpu className="h-4 w-4 text-cyan-400" /> Affected neurons (top features by |weight|)
                      </p>
                      <div className="space-y-2">
                        {footprint.data.affected_neurons.map((n) => (
                          <div key={n.feature} className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2 text-sm">
                            <span className="text-slate-300">{n.feature}</span>
                            <span className="mono text-xs text-slate-500">{n.weight.toFixed(5)}</span>
                          </div>
                        ))}
                        {footprint.data.affected_neurons.length === 0 && (
                          <p className="text-sm text-slate-500">No trained model yet for this data.</p>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-slate-800/70 pt-5">
                    <div className="mr-auto flex items-center gap-2 text-sm text-slate-400">
                      <span>Method:</span>
                      <Select value={method} onChange={(e) => setMethod(e.target.value)} className="w-44">
                        <option value="retrain">SISA retrain (gold standard)</option>
                        <option value="certified">Certified Newton removal</option>
                        <option value="influence">Influence gradient scrub</option>
                      </Select>
                    </div>
                    <Button variant="danger" onClick={() => deleteSelected.mutate()} loading={deleteSelected.isPending}>
                      <Trash2 className="h-4 w-4" /> Selective unlearning
                    </Button>
                    <Button variant="outline" onClick={() => fullReset.mutate()} loading={fullReset.isPending}>
                      Complete identity reset
                    </Button>
                  </div>
                </CardContent>
              ) : null}
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {activeRequest && (
        <Card className="border-violet-500/30">
          <CardHeader>
            <CardTitle>Deletion Pipeline — {request.data?.id ? shortHash(request.data.id, 12) : "..."}</CardTitle>
            <Badge tone={done ? "emerald" : failed ? "rose" : "amber"}>{request.data?.status ?? "queued"}</Badge>
          </CardHeader>
          <CardContent>
            {!done && !failed && (
              <>
                <Progress value={request.data ? 65 : 20} className="mb-3" />
                <p className="text-sm text-slate-400">
                  Tombstoning records → scrubbing shards → recomputing Merkle roots → signing certificate…
                </p>
              </>
            )}
            {done && request.data?.certificate_id && (
              <div className="space-y-3">
                <p className="text-sm text-emerald-300">Deletion completed and certified.</p>
                <div className="mono grid gap-2 rounded-lg border border-slate-800 bg-slate-900/50 p-4 text-xs md:grid-cols-2">
                  <span className="text-slate-500">certificate <Link className="text-cyan-400 hover:underline" href={`/certificates/${request.data.certificate_id}`}>{shortHash(request.data.certificate_id, 14)}</Link></span>
                  <span className="text-slate-500">status <span className="text-emerald-300">{request.data.status}</span></span>
                </div>
                <div className="flex flex-wrap gap-3">
                  <Button onClick={() => verify.mutate(request.data.certificate_id!)} loading={verify.isPending}>
                    <FileCheck2 className="h-4 w-4" /> Verify certificate
                  </Button>
                  <Button variant="outline" onClick={() => setActiveRequest(null)}>Done</Button>
                </div>
              </div>
            )}
            {failed && (
              <p className="text-sm text-rose-300">Request failed: {request.data?.error}</p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
