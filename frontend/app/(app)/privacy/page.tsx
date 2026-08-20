"use client";

import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
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
  FileSearch,
  History,
  FileText,
  MessageSquare,
  ChevronDown,
  Maximize2,
  X,
  ShieldCheck,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress, Spinner } from "@/components/ui/progress";
import { Table, THead, Th, Td, TRow } from "@/components/ui/table";
import { Select } from "@/components/ui/select";
import { shortHash, timeAgo } from "@/lib/utils";

interface ChatSession {
  session_id: string;
  name: string;
  content: string;
  messages: { role: string; content: string }[];
  message_count: number;
  sensitive_data: string;
  updated_at: string | null;
}

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
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Match | null>(null);
  const [method, setMethod] = useState("retrain");
  const [activeRequest, setActiveRequest] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [scanReportId, setScanReportId] = useState<string | null>(null);
  const [chatHistoryOpen, setChatHistoryOpen] = useState(false);
  const [fullscreenChat, setFullscreenChat] = useState<ChatSession | null>(null);
  const chatHistoryRef = useRef<HTMLDivElement>(null);

  const chatHistory = useQuery<{ sessions: ChatSession[] }>({
    queryKey: ["privacy-chat-history"],
    queryFn: () => api.get("/api/v1/assistant/sessions"),
    refetchInterval: 5000,
    enabled: chatHistoryOpen,
  });

  const search = useMutation({
    mutationFn: (q: string) => api.post<{ matches: Match[] }>(`/api/v1/privacy/search?query=${encodeURIComponent(q)}`),
    onError: (e) => setNotice(e instanceof ApiError ? e.message : "Search failed"),
  });

  const scan = useMutation({
    mutationFn: () =>
      api.post<{ report_id: string; scanned_records: number; findings_count: number; risk_score: number }>(
        "/api/v1/privacy/scan"
      ),
    onSuccess: (data) => {
      setNotice(
        `Scan complete — ${data.scanned_records} records, ${data.findings_count} PII findings, risk ${data.risk_score}/100.`
      );
      setScanReportId(data.report_id);
    },
    onError: (e) => setNotice(e instanceof ApiError ? e.message : "Scan failed"),
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

      <div className="flex flex-wrap items-center gap-3">
        <Card className="flex-1 min-w-[280px]">
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
                  placeholder="Search name, email, phone, Aadhaar, PAN, chat id…"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && search.mutate(query)}
                />
              </div>
              <Button onClick={() => search.mutate(query)} loading={search.isPending}>
                Audit all shards
              </Button>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-500">
              <Link href="/privacy/history" className="flex items-center gap-1 text-cyan-400 hover:underline">
                <History className="h-3.5 w-3.5" /> Search history
              </Link>
              <span className="text-slate-700">·</span>
              <div className="relative" ref={chatHistoryRef}>
                <button
                  onClick={() => setChatHistoryOpen((v) => !v)}
                  className="flex items-center gap-1 rounded-md border border-slate-700 px-2 py-1 text-cyan-400 transition-colors hover:bg-slate-800/60"
                >
                  <MessageSquare className="h-3.5 w-3.5" />
                  Chat history
                  <ChevronDown className={`h-3 w-3 transition-transform ${chatHistoryOpen ? "rotate-180" : ""}`} />
                </button>
                <AnimatePresence>
                  {chatHistoryOpen && (
                    <motion.div
                      initial={{ opacity: 0, y: -6 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -6 }}
                      className="absolute left-0 top-full z-30 mt-2 w-96 overflow-hidden rounded-xl border border-slate-700 bg-slate-900/95 shadow-xl backdrop-blur"
                    >
                      <div className="border-b border-slate-800 px-3 py-2 text-[11px] uppercase tracking-wider text-slate-500">
                        Saved chats · {chatHistory.data?.sessions.length ?? 0}
                      </div>
                      <div className="max-h-80 overflow-y-auto p-1.5">
                        {chatHistory.isLoading ? (
                          <div className="flex justify-center py-6">
                            <Spinner />
                          </div>
                        ) : (chatHistory.data?.sessions ?? []).length === 0 ? (
                          <p className="px-3 py-6 text-center text-xs text-slate-500">
                            No chats saved yet — chats stay saved per account after refreshing or logging out.
                          </p>
                        ) : (
                          (chatHistory.data?.sessions ?? []).map((s) => {
                            const msgs = s.messages?.length ? s.messages : parseTranscript(s.content);
                            return (
                              <div
                                key={s.session_id}
                                onClick={() => setFullscreenChat(s)}
                                className="group mb-1.5 cursor-pointer rounded-lg border border-slate-800 bg-slate-900/40 transition-colors hover:border-cyan-500/40 hover:bg-slate-900/70"
                              >
                                <div className="flex items-center justify-between gap-2 px-3 pt-2">
                                  <div className="min-w-0">
                                    <p className="truncate text-xs font-semibold text-slate-200">{s.name || "Untitled chat"}</p>
                                    <p className="mono text-[10px] text-slate-600">
                                      {s.session_id.slice(0, 8)}… · {s.message_count} msgs · {timeAgo(s.updated_at)}
                                    </p>
                                  </div>
                                  <span className="flex shrink-0 items-center gap-1 rounded-md border border-slate-700 px-2 py-1 text-[10px] text-cyan-400 transition-colors group-hover:border-cyan-500/40">
                                    <Maximize2 className="h-3 w-3" /> Full screen
                                  </span>
                                </div>
                                <ol className="mt-1.5 space-y-1 border-t border-slate-800/70 px-3 py-2">
                                  {msgs.map((m, i) => (
                                    <li key={i} className="flex items-start gap-2 text-[11px] leading-snug">
                                      <span
                                        className={`mono mt-0.5 shrink-0 rounded px-1 py-px text-[9px] ${
                                          m.role === "user"
                                            ? "bg-cyan-500/15 text-cyan-300"
                                            : "bg-violet-500/15 text-violet-300"
                                        }`}
                                      >
                                        {m.role === "user" ? "you" : "ai"}
                                      </span>
                                      <span className="line-clamp-2 min-w-0 text-slate-400">{m.content || "…"}</span>
                                    </li>
                                  ))}
                                </ol>
                              </div>
                            );
                          })
                        )}
                      </div>
                      <div className="border-t border-slate-800 px-3 py-1.5 text-[10px] text-slate-600">
                        History is stored permanently per account.
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
              <span className="text-slate-700">·</span>
              <span>structured filters supported (email, phone, aadhaar, pan, record_id, chat_id)</span>
            </div>
          </CardContent>
        </Card>
        <Card className="min-w-[280px]">
          <CardHeader>
            <CardTitle>Privacy Scan</CardTitle>
            <FileSearch className="h-5 w-5 text-violet-400" />
          </CardHeader>
          <CardContent>
            <p className="mb-3 text-sm text-slate-500">
              Full-dataset PII detection — categories, severity, risk score, persisted report.
            </p>
            <div className="flex items-center gap-3">
              <Button variant="outline" onClick={() => scan.mutate()} loading={scan.isPending}>
                <FileSearch className="h-4 w-4" /> Scan all datasets
              </Button>
              {scanReportId && (
                <Link href={`/privacy/report/${scanReportId}`}>
                  <Button>
                    <FileText className="h-4 w-4" /> View report
                  </Button>
                </Link>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

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
                <div className="flex items-center gap-2">
                  <Link href={`/privacy/records?id=${m.record_id}`} target="_blank">
                    <Button variant="ghost" size="sm">
                      <FileText className="h-3.5 w-3.5" /> View
                    </Button>
                  </Link>
                  <Button variant="outline" size="sm" onClick={() => setSelected(m)}>
                    <Eye className="h-3.5 w-3.5" /> Footprint
                  </Button>
                </div>
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

      {/* full-screen chat view */}
      <AnimatePresence>
        {fullscreenChat && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/85 p-3 backdrop-blur-sm sm:p-6"
            onClick={() => setFullscreenChat(null)}
          >
            <motion.div
              initial={{ scale: 0.97, y: 12 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.97, y: 12 }}
              onClick={(e) => e.stopPropagation()}
              className="flex h-full w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl"
            >
              <div className="flex items-start justify-between gap-3 border-b border-slate-800 px-6 py-4">
                <div className="min-w-0">
                  <h2 className="truncate text-lg font-semibold text-slate-100">
                    {fullscreenChat.name || "Untitled chat"}
                  </h2>
                  <p className="mono mt-0.5 text-xs text-slate-500">
                    {fullscreenChat.session_id} · {fullscreenChat.message_count} messages · {timeAgo(fullscreenChat.updated_at)}
                  </p>
                </div>
                <button
                  onClick={() => setFullscreenChat(null)}
                  className="shrink-0 rounded-lg border border-slate-700 p-1.5 text-slate-400 transition-colors hover:bg-slate-800"
                  aria-label="Close"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="min-h-0 flex-1 overflow-y-auto p-6">
                <div className="space-y-4">
                  {(fullscreenChat.messages?.length
                    ? fullscreenChat.messages
                    : parseTranscript(fullscreenChat.content)
                  ).map((m, i) => (
                    <div key={i} className="flex justify-start">
                      <div
                        className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                          m.role === "user"
                            ? "rounded-bl-md bg-cyan-500/90 text-slate-950"
                            : "rounded-bl-md border border-slate-700/60 bg-slate-800/60 text-slate-200"
                        }`}
                      >
                        <span
                          className={`mono mb-1 block text-[9px] uppercase tracking-wider ${
                            m.role === "user" ? "text-slate-700" : "text-violet-300/70"
                          }`}
                        >
                          {m.role === "user" ? "You" : "Assistant"}
                        </span>
                        {m.content}
                      </div>
                    </div>
                  ))}
                  {fullscreenChat.sensitive_data && (
                    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-rose-500/20 bg-rose-500/5 px-4 py-3 text-sm text-rose-200">
                      <ShieldAlert className="h-4 w-4 shrink-0" />
                      <span className="font-medium">Sensitive data detected:</span>
                      {fullscreenChat.sensitive_data.split(",").map((c) => (
                        <Badge key={c} tone="rose">{c.trim()}</Badge>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-3 border-t border-slate-800 px-6 py-4">
                <span className="mr-auto text-xs text-slate-500">
                  Choose how to prune this chat — you&apos;ll continue on the unlearning page.
                </span>
                <Button
                  variant="outline"
                  disabled={!fullscreenChat.sensitive_data}
                  onClick={() =>
                    router.push(`/unlearning?chat=${encodeURIComponent(fullscreenChat.session_id)}&mode=sensitive`)
                  }
                >
                  <ShieldCheck className="h-4 w-4" /> Scrub sensitive data
                </Button>
                <Button
                  variant="danger"
                  onClick={() =>
                    router.push(`/unlearning?chat=${encodeURIComponent(fullscreenChat.session_id)}&mode=full`)
                  }
                >
                  <Trash2 className="h-4 w-4" /> Full prune
                </Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function parseTranscript(content: string): { role: string; content: string }[] {
  const msgs: { role: string; content: string }[] = [];
  for (const line of content.split("\n")) {
    const m = /^(user|assistant):\s?(.*)$/.exec(line);
    if (m) msgs.push({ role: m[1], content: m[2] });
  }
  return msgs;
}
