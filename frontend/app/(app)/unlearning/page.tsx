"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Trash2,
  Scissors,
  Search,
  CalendarClock,
  FileCheck2,
  ShieldCheck,
  ShieldAlert,
  ArrowRight,
  CheckCircle2,
  XCircle,
  Download,
  Eye,
  RotateCcw,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/progress";
import { shortHash, timeAgo } from "@/lib/utils";

interface ChatSession {
  session_id: string;
  name: string;
  content: string;
  sensitive_data: string;
  message_count: number;
  created_at: string | null;
  updated_at: string | null;
}

interface DeleteOut {
  chat_session_id: string;
  mode: string;
  certificate_id: string;
  deletion_type: string;
  method: string;
  deleted_record_count: number;
  pre_merkle_root: string;
  post_merkle_root: string;
  sensitive_categories: string[];
  verification_status: string;
  timestamp: string;
}

interface VerifyRun {
  report_id: string;
  verdict: string;
  checks_passed: number;
  checks_total: number;
  duration_seconds: number;
  certificate_id: string;
}

interface Filters {
  search: string;
  from: string;
  to: string;
}

export default function UnlearningPage() {
  const qc = useQueryClient();
  const params = useSearchParams();
  const [searchInput, setSearchInput] = useState("");
  const [fromInput, setFromInput] = useState("");
  const [toInput, setToInput] = useState("");
  const [filters, setFilters] = useState<Filters | null>(null);
  const [selected, setSelected] = useState<ChatSession | null>(null);
  const [confirmMode, setConfirmMode] = useState<"full" | "sensitive" | null>(null);
  const [result, setResult] = useState<DeleteOut | null>(null);
  const [notice, setNotice] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  // ---- deep link: ?chat=<id>&mode=full|sensitive pre-loads a chat for pruning ----
  const [deepLinked, setDeepLinked] = useState(false);
  const deepChatId = params.get("chat");
  const deepMode = params.get("mode");

  // ---- search chat sessions (static + real-time polling while active) ----
  const sessions = useQuery<{ sessions: ChatSession[] }>({
    queryKey: ["chat-deletions", filters],
    queryFn: () => {
      const p = new URLSearchParams();
      if (filters?.search) p.set("search", filters.search);
      if (filters?.from) p.set("from", filters.from);
      if (filters?.to) p.set("to", filters.to);
      const qs = p.toString();
      return api.get(`/api/v1/assistant/sessions${qs ? `?${qs}` : ""}`);
    },
    enabled: !!filters,
    refetchInterval: filters ? 3000 : false,
  });

  useEffect(() => {
    if (deepLinked || !deepChatId) return;
    setDeepLinked(true);
    setSearchInput(deepChatId);
    setFilters({ search: deepChatId, from: "", to: "" });
  }, [deepLinked, deepChatId]);

  useEffect(() => {
    if (!deepChatId || !filters || !sessions.data) return;
    const match = sessions.data.sessions.find((s) => s.session_id === deepChatId);
    if (!match || selected?.session_id === match.session_id) return;
    setSelected(match);
    setResult(null);
    setConfirmMode(deepMode === "full" || deepMode === "sensitive" ? deepMode : null);
  }, [deepChatId, deepMode, filters, sessions.data, selected?.session_id]);

  // ---- deletion execution ----
  const del = useMutation({
    mutationFn: ({ id, mode }: { id: string; mode: "full" | "sensitive" }) =>
      api.post<DeleteOut>(`/api/v1/unlearning/chats/${id}/delete`, { mode }),
    onSuccess: (out) => {
      setResult(out);
      setNotice({ kind: "ok", text: `Chat ${out.mode} deletion completed — certificate minted.` });
      setConfirmMode(null);
      qc.invalidateQueries({ queryKey: ["chat-deletions"] });
      qc.invalidateQueries({ queryKey: ["certificates"] });
      qc.invalidateQueries({ queryKey: ["audit-sessions"] });
      verify.mutate(out.certificate_id);
    },
    onError: (e) => setNotice({ kind: "err", text: e instanceof ApiError ? e.message : "Deletion failed" }),
  });

  // ---- feed the freshly minted certificate into verification ----
  const verify = useMutation({
    mutationFn: (certificateId: string) =>
      api.post<VerifyRun>("/api/v1/verification/run", { certificate_id: certificateId }),
    onError: (e) => setNotice({ kind: "err", text: e instanceof ApiError ? e.message : "Verification failed" }),
  });

  const runSearch = () => {
    setResult(null);
    setSelected(null);
    setFilters({
      search: searchInput.trim(),
      from: fromInput ? new Date(fromInput).toISOString() : "",
      to: toInput ? new Date(toInput).toISOString() : "",
    });
  };

  const reset = () => {
    setFilters(null);
    setSearchInput("");
    setFromInput("");
    setToInput("");
    setSelected(null);
    setResult(null);
    setConfirmMode(null);
  };

  const rows = sessions.data?.sessions ?? [];
  const sensitiveCategories = selected
    ? selected.sensitive_data.split(",").map((s) => s.trim()).filter(Boolean)
    : [];

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold tracking-tight">Surgical Machine Unlearning</h1>
        <p className="mt-1 text-sm text-slate-500">
          Search Assistant conversations → delete sensitive data or the whole chat → signed deletion certificate → verification.
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

      {/* STEP 1 — search */}
      <Card>
        <CardHeader>
          <CardTitle>
            <span className="flex items-center gap-2"><Search className="h-4 w-4 text-cyan-400" /> Step 1 · Find a chat conversation</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
            <div className="lg:col-span-1">
              <Label>Chat ID</Label>
              <Input placeholder="chat session id — e.g. 3f2a…" value={searchInput} onChange={(e) => setSearchInput(e.target.value)} />
            </div>
            <div>
              <Label>From (date &amp; time)</Label>
              <Input type="datetime-local" value={fromInput} onChange={(e) => setFromInput(e.target.value)} />
            </div>
            <div>
              <Label>To (date &amp; time)</Label>
              <Input type="datetime-local" value={toInput} onChange={(e) => setToInput(e.target.value)} />
            </div>
            <div className="flex items-end gap-2">
              <Button onClick={runSearch} loading={sessions.isFetching && !!filters}>
                <Search className="h-4 w-4" /> Search
              </Button>
              <Button variant="outline" onClick={reset} disabled={!filters && !searchInput && !fromInput && !toInput}>
                <RotateCcw className="h-4 w-4" /> Reset
              </Button>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-500">
            <CalendarClock className="h-3.5 w-3.5" />
            {filters ? (
              <span>
                Showing matches for <span className="text-slate-300">{filters.search || "all chats"}</span>
                {filters.from && <span> · after {new Date(filters.from).toLocaleString()}</span>}
                {filters.to && <span> · before {new Date(filters.to).toLocaleString()}</span>}
                {" "}— live, refreshes every 3s.
              </span>
            ) : (
              <span>Enter a chat id and/or a date range to search. Live results update every 3s.</span>
            )}
          </div>

          {filters && sessions.isLoading ? (
            <div className="flex justify-center py-10"><Spinner /></div>
          ) : filters ? (
            rows.length > 0 ? (
              <div className="max-h-80 overflow-auto rounded-xl border border-slate-800">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-slate-900 text-left text-[11px] uppercase tracking-wider text-slate-500">
                    <tr>
                      <th className="px-3 py-2">Chat ID</th>
                      <th className="px-3 py-2">Chat name</th>
                      <th className="px-3 py-2">Messages</th>
                      <th className="px-3 py-2">Sensitive data</th>
                      <th className="px-3 py-2">Updated</th>
                      <th className="px-3 py-2"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((c) => (
                      <tr
                        key={c.session_id}
                        className={`cursor-pointer border-t border-slate-800/60 transition-colors hover:bg-slate-900/40 ${
                          selected?.session_id === c.session_id ? "bg-cyan-500/5" : ""
                        }`}
                        onClick={() => {
                          setSelected(c);
                          setResult(null);
                          setConfirmMode(null);
                        }}
                      >
                        <td className="mono px-3 py-2 text-xs text-cyan-300">{shortHash(c.session_id, 10)}</td>
                        <td className="px-3 py-2">
                          <span className="font-medium text-slate-200">{c.name || "Untitled chat"}</span>
                          <span className="mono block truncate text-xs text-slate-500">{c.session_id}</span>
                        </td>
                        <td className="px-3 py-2 text-xs text-slate-400">{c.message_count}</td>
                        <td className="px-3 py-2 text-xs">
                          {c.sensitive_data ? <Badge tone="rose">{c.sensitive_data}</Badge> : <span className="text-slate-600">none</span>}
                        </td>
                        <td className="px-3 py-2 text-xs text-slate-500">{timeAgo(c.updated_at)}</td>
                        <td className="px-3 py-2 text-right">
                          <Eye className="inline h-4 w-4 text-slate-500" />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="py-8 text-center text-sm text-slate-500">No chat sessions match your search.</p>
            )
          ) : null}
        </CardContent>
      </Card>

      {/* STEP 2 — selected chat + deletion options */}
      <AnimatePresence>
        {selected && (
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 16 }}>
            <Card className="border-violet-500/30">
              <CardHeader>
                <CardTitle>
                  <span className="flex items-center gap-2">
                    <Scissors className="h-4 w-4 text-violet-400" /> Step 2 · {selected.name || "Untitled chat"}
                  </span>
                </CardTitle>
                <Badge tone="cyan" className="mono">{selected.session_id}</Badge>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3 text-xs sm:grid-cols-3">
                  <div className="rounded-lg bg-slate-950/50 px-3 py-2">
                    <p className="text-slate-500">messages</p>
                    <p className="mt-0.5 font-semibold text-slate-200">{selected.message_count}</p>
                  </div>
                  <div className="rounded-lg bg-slate-950/50 px-3 py-2">
                    <p className="text-slate-500">last updated</p>
                    <p className="mt-0.5 font-semibold text-slate-200">{timeAgo(selected.updated_at)}</p>
                  </div>
                  <div className="rounded-lg bg-slate-950/50 px-3 py-2">
                    <p className="text-slate-500">sensitive data</p>
                    <p className="mt-0.5 font-semibold text-slate-200">
                      {sensitiveCategories.length > 0 ? sensitiveCategories.join(", ") : "none"}
                    </p>
                  </div>
                </div>

                <div>
                  <p className="mb-2 text-[10px] uppercase tracking-wider text-slate-500">Conversation preview</p>
                  <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-xs leading-relaxed text-slate-300">
                    {selected.content || "— empty —"}
                  </pre>
                </div>

                {sensitiveCategories.length > 0 && (
                  <div className="flex items-start gap-2 rounded-lg border border-rose-500/20 bg-rose-500/5 p-3 text-sm text-rose-200">
                    <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
                    This conversation contains <span className="font-medium">{sensitiveCategories.join(", ")}</span>.{" "}
                    Unlearn it partially (scrub sensitive data only) or fully (delete the entire conversation).
                  </div>
                )}

                <div className="flex flex-wrap items-center gap-3 border-t border-slate-800/70 pt-4">
                  <Button
                    variant="outline"
                    onClick={() => setConfirmMode(confirmMode === "sensitive" ? null : "sensitive")}
                    loading={del.isPending && confirmMode === "sensitive"}
                    disabled={del.isPending || sensitiveCategories.length === 0}
                  >
                    <ShieldCheck className="h-4 w-4" /> Delete sensitive data only
                  </Button>
                  <Button
                    variant="danger"
                    onClick={() => setConfirmMode(confirmMode === "full" ? null : "full")}
                    loading={del.isPending && confirmMode === "full"}
                    disabled={del.isPending}
                  >
                    <Trash2 className="h-4 w-4" /> Delete entire chat
                  </Button>
                  <span className="text-xs text-slate-500">
                    Either deletion mints a signed certificate and runs verification.
                  </span>
                </div>

                {confirmMode && (
                  <div className="flex flex-wrap items-center gap-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm">
                    <span className="text-amber-200">
                      {confirmMode === "full"
                        ? `Permanently delete this entire conversation (${selected.message_count} messages)?`
                        : `Scrub all sensitive data from this conversation, keeping the rest?`}
                    </span>
                    <div className="ml-auto flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => setConfirmMode(null)}>
                        Cancel
                      </Button>
                      <Button
                        size="sm"
                        variant={confirmMode === "full" ? "danger" : "primary"}
                        loading={del.isPending}
                        onClick={() => del.mutate({ id: selected.session_id, mode: confirmMode })}
                      >
                        <CheckCircle2 className="h-4 w-4" /> Confirm
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* STEP 3 — certificate + verification */}
      <AnimatePresence>
        {result && (
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 16 }}>
            <Card className="border-emerald-500/30">
              <CardHeader>
                <CardTitle>
                  <span className="flex items-center gap-2">
                    <FileCheck2 className="h-4 w-4 text-emerald-400" /> Step 3 · Deletion certificate + verification
                  </span>
                </CardTitle>
                <Badge tone={result.verification_status === "valid" ? "emerald" : "amber"}>{result.verification_status}</Badge>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-start gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-200">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                  {result.mode === "full" ? "Entire conversation deleted." : "Sensitive data scrubbed, conversation preserved."}{" "}
                  Certificate <span className="mono text-cyan-300">{shortHash(result.certificate_id, 18)}</span> issued and stored in Certificates.
                </div>

                <div className="grid gap-3 text-xs sm:grid-cols-2 lg:grid-cols-4">
                  <div className="rounded-lg bg-slate-950/50 px-3 py-2">
                    <p className="text-slate-500">method</p>
                    <p className="mono mt-0.5 font-semibold text-slate-200">{result.method}</p>
                  </div>
                  <div className="rounded-lg bg-slate-950/50 px-3 py-2">
                    <p className="text-slate-500">segments removed</p>
                    <p className="mt-0.5 font-semibold text-rose-300">{result.deleted_record_count}</p>
                  </div>
                  <div className="rounded-lg bg-slate-950/50 px-3 py-2">
                    <p className="text-slate-500">sensitive categories</p>
                    <p className="mt-0.5 font-semibold text-slate-200">{result.sensitive_categories.join(", ") || "—"}</p>
                  </div>
                  <div className="rounded-lg bg-slate-950/50 px-3 py-2">
                    <p className="text-slate-500">merkle transition</p>
                    <p className="mono mt-0.5 break-all text-slate-200">
                      <span className="text-slate-500">{result.pre_merkle_root.slice(0, 8)}</span>
                      <span className="text-cyan-500"> → </span>
                      <span className="text-cyan-300">{result.post_merkle_root.slice(0, 8)}</span>
                    </p>
                  </div>
                </div>

                {verify.isPending && (
                  <p className="flex items-center gap-2 text-sm text-slate-400">
                    <Spinner className="h-4 w-4" /> Feeding certificate into the verification engine…
                  </p>
                )}
                {verify.data && (
                  <div
                    className={`flex items-start gap-2 rounded-lg border px-4 py-3 text-sm ${
                      verify.data.verdict === "valid"
                        ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
                        : "border-rose-500/30 bg-rose-500/10 text-rose-200"
                    }`}
                  >
                    {verify.data.verdict === "valid" ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> : <XCircle className="mt-0.5 h-4 w-4 shrink-0" />}
                    Verification <span className="font-semibold uppercase">{verify.data.verdict}</span> —{" "}
                    {verify.data.checks_passed}/{verify.data.checks_total} checks in {verify.data.duration_seconds}s.
                  </div>
                )}
                {verify.isError && (
                  <div className="flex items-start gap-2 rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-200">
                    <XCircle className="mt-0.5 h-4 w-4 shrink-0" />
                    Verification could not run: {verify.error instanceof ApiError ? verify.error.message : "unexpected error"}
                  </div>
                )}

                <div className="flex flex-wrap items-center gap-3 border-t border-slate-800/70 pt-4">
                  <Link href={`/certificates/${result.certificate_id}`}>
                    <Button>
                      <FileCheck2 className="h-4 w-4" /> Open certificate
                    </Button>
                  </Link>
                  <Button variant="outline" onClick={() => api.download(`/api/v1/certificates/${result.certificate_id}/pdf`, `certificate-${result.certificate_id}.pdf`)}>
                    <Download className="h-4 w-4" /> PDF
                  </Button>
                  <Button variant="outline" onClick={() => api.download(`/api/v1/certificates/${result.certificate_id}/download`, `certificate-${result.certificate_id}.json`)}>
                    <Download className="h-4 w-4" /> JSON
                  </Button>
                  {verify.data && (
                    <Link href={`/verification/${verify.data.report_id}`} className="ml-auto">
                      <Button variant="ghost">
                        View report <ArrowRight className="ml-1 h-3.5 w-3.5" />
                      </Button>
                    </Link>
                  )}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {!filters && !selected && !result && (
        <p className="text-center text-sm text-slate-500">
          Start by searching a chat conversation above — by chat id and/or date &amp; time.
        </p>
      )}
    </div>
  );
}