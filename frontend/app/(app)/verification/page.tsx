"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  ShieldCheck,
  Play,
  FileCheck2,
  ScrollText,
  Gauge,
  ArrowRight,
  ShieldAlert,
  KeyRound,
  Download,
  CheckCircle2,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/ui/stat";
import { Select } from "@/components/ui/select";
import { Spinner } from "@/components/ui/progress";
import { shortHash, timeAgo } from "@/lib/utils";

interface ReportSummary {
  id: string;
  certificate_id: string;
  deletion_request_id: string | null;
  dataset_id: string | null;
  verdict: string;
  checks_passed: number;
  checks_total: number;
  duration_seconds: number | null;
  created_by: string;
  created_at: string | null;
}

interface Certificate {
  id: string;
  subject_user_id: string;
  deletion_type: string;
  deleted_record_count: number;
  pre_merkle_root: string;
  post_merkle_root: string;
  method: string;
  verification_status: string;
  created_at: string | null;
}

export default function VerificationPage() {
  const qc = useQueryClient();
  const [certId, setCertId] = useState("");
  const [scope, setScope] = useState<"certificate" | "dataset">("certificate");
  const [datasetFilter, setDatasetFilter] = useState("");
  const [notice, setNotice] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  const certificates = useQuery<Certificate[]>({
    queryKey: ["certificates"],
    queryFn: () => api.get("/api/v1/certificates?limit=100"),
  });

  const history = useQuery<{ reports: ReportSummary[] }>({
    queryKey: ["verification-history"],
    queryFn: () => api.get("/api/v1/verification/history"),
  });

  const run = useMutation({
    mutationFn: () =>
      api.post<{ report_id: string; verdict: string; checks_passed: number; checks_total: number; duration_seconds: number }>(
        "/api/v1/verification/run",
        { certificate_id: scope === "certificate" ? certId || undefined : undefined, dataset_id: scope === "dataset" ? datasetFilter || undefined : undefined }
      ),
    onSuccess: async (data) => {
      setNotice({
        kind: data.verdict === "valid" ? "ok" : "err",
        text: `Verification ${data.verdict.toUpperCase()} — ${data.checks_passed}/${data.checks_total} checks in ${data.duration_seconds}s.`,
      });
      await qc.invalidateQueries({ queryKey: ["verification-history"] });
      await qc.invalidateQueries({ queryKey: ["certificates"] });
    },
    onError: (e) => setNotice({ kind: "err", text: e instanceof ApiError ? e.message : "Verification failed" }),
  });

  const publicKey = useQuery<{ public_key_pem: string }>({
    queryKey: ["public-key"],
    queryFn: () => api.get("/api/v1/verification/public-key"),
    enabled: false,
  });

  const stats = (history.data?.reports ?? []).reduce(
    (acc, r) => {
      acc.total += 1;
      if (r.verdict === "valid") acc.valid += 1;
      acc.checks += r.checks_passed;
      return acc;
    },
    { total: 0, valid: 0, checks: 0 }
  );

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold tracking-tight">Verifiable Machine Unlearning</h1>
        <p className="mt-1 text-sm text-slate-500">
          Cryptographic evidence that deletions are valid and complete — records, embeddings, vectors, Merkle roots, signatures, audit chain.
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
          {notice.kind === "ok" ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> : <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />}
          {notice.text}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Reports run" value={stats.total} icon={<Gauge className="h-4 w-4" />} accent="text-cyan-400" />
        <StatCard label="Valid verdicts" value={stats.valid} icon={<ShieldCheck className="h-4 w-4" />} accent="text-emerald-400" />
        <StatCard label="Checks passed" value={stats.checks} icon={<FileCheck2 className="h-4 w-4" />} accent="text-violet-400" />
      </div>

      {/* run verification */}
      <Card>
        <CardHeader>
          <CardTitle>
            <span className="flex items-center gap-2"><Play className="h-4 w-4 text-cyan-400" /> Run verification</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-sm text-slate-400">Target:</span>
            <div className="flex gap-2">
              {(["certificate", "dataset"] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => setScope(s)}
                  className={`rounded-lg border px-3 py-2 text-sm capitalize transition-colors ${
                    scope === s ? "border-cyan-400/50 bg-cyan-500/10 text-cyan-300" : "border-slate-700 text-slate-400 hover:bg-slate-800/50"
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          {scope === "certificate" ? (
            <div className="flex flex-wrap items-center gap-3">
              <Select value={certId} onChange={(e) => setCertId(e.target.value)} className="min-w-[320px] flex-1">
                <option value="">— select a certificate —</option>
                {(certificates.data ?? []).map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.subject_user_id} · {c.deletion_type} · {c.deleted_record_count} records · {c.id.slice(0, 8)}
                  </option>
                ))}
              </Select>
              <Button onClick={() => run.mutate()} loading={run.isPending} disabled={!certId}>
                <ShieldCheck className="h-4 w-4" /> Run verification
              </Button>
            </div>
          ) : (
            <DatasetPicker value={datasetFilter} onChange={setDatasetFilter} />
          )}
        </CardContent>
      </Card>

      {/* verification flow */}
      <Card className="border-emerald-500/20">
        <CardHeader>
          <CardTitle>Verification pipeline</CardTitle>
          <ShieldCheck className="h-5 w-5 text-emerald-400" />
        </CardHeader>
        <CardContent>
          <FlowSteps />
        </CardContent>
      </Card>

      {/* history */}
      <Card>
        <CardHeader>
          <CardTitle>Verification reports</CardTitle>
          <ScrollText className="h-5 w-5 text-cyan-400" />
        </CardHeader>
        <CardContent>
          {history.isLoading ? (
            <div className="flex justify-center py-10"><Spinner /></div>
          ) : history.data && history.data.reports.length > 0 ? (
            <div className="space-y-2">
              {history.data.reports.map((r, i) => (
                <motion.div
                  key={r.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3"
                >
                  <span className={`h-2.5 w-2.5 rounded-full ${r.verdict === "valid" ? "bg-emerald-400" : "bg-rose-400"}`} />
                  <span className="mono text-xs font-semibold text-cyan-300">{r.id.slice(0, 10)}</span>
                  <Badge tone={r.verdict === "valid" ? "emerald" : "rose"}>{r.verdict}</Badge>
                  <span className="mono text-xs text-slate-500">
                    {r.checks_passed}/{r.checks_total} checks · {r.duration_seconds}s
                  </span>
                  <span className="mono hidden text-xs text-slate-600 md:inline">cert {shortHash(r.certificate_id, 10)}</span>
                  <span className="ml-auto text-xs text-slate-500">{timeAgo(r.created_at)}</span>
                  <Link href={`/verification/${r.id}`}>
                    <Button variant="outline" size="sm">
                      Open <ArrowRight className="ml-1 h-3.5 w-3.5" />
                    </Button>
                  </Link>
                </motion.div>
              ))}
            </div>
          ) : (
            <p className="py-10 text-center text-sm text-slate-500">No verification reports yet — run one above.</p>
          )}
        </CardContent>
      </Card>

      {/* public key for external verification */}
      <Card>
        <CardHeader>
          <CardTitle>
            <span className="flex items-center gap-2"><KeyRound className="h-4 w-4 text-amber-400" /> External verification key</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-3 text-sm text-slate-500">
            The RSA public key below lets any third party independently verify certificate signatures and proofs.
          </p>
          <div className="flex items-center gap-3">
            <Button variant="outline" onClick={() => publicKey.refetch()} loading={publicKey.isFetching}>
              <KeyRound className="h-4 w-4" /> Fetch public key
            </Button>
            {publicKey.data && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  const blob = new Blob([publicKey.data.public_key_pem], { type: "text/plain" });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = "veriunlearn-public-key.pem";
                  a.click();
                  URL.revokeObjectURL(url);
                }}
              >
                <Download className="h-3.5 w-3.5" /> Download .pem
              </Button>
            )}
          </div>
          {publicKey.data && (
            <pre className="mono mt-3 max-h-40 overflow-auto rounded-lg border border-slate-800 bg-slate-950/60 p-4 text-[11px] text-emerald-300">
              {publicKey.data.public_key_pem}
            </pre>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function FlowSteps() {
  const steps = [
    { label: "Deletion", desc: "records tombstoned" },
    { label: "Retraining", desc: "shards scrubbed" },
    { label: "Verification", desc: "8 checks run" },
    { label: "Merkle", desc: "roots recomputed" },
    { label: "Signature", desc: "RSA verified" },
    { label: "Certificate", desc: "bound to roots" },
    { label: "Audit", desc: "chain intact" },
    { label: "Completed", desc: "report issued" },
  ];
  return (
    <div className="flex flex-wrap items-center gap-2">
      {steps.map((s, i) => (
        <div key={s.label} className="flex items-center gap-2">
          <div className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/50 px-3 py-2">
            <span className={`h-2 w-2 rounded-full ${i < 3 ? "bg-cyan-400" : i < 7 ? "bg-violet-400" : "bg-emerald-400"}`} />
            <div>
              <p className="text-xs font-semibold text-slate-200">{s.label}</p>
              <p className="text-[10px] text-slate-500">{s.desc}</p>
            </div>
          </div>
          {i < steps.length - 1 && <ArrowRight className="h-3.5 w-3.5 text-slate-600" />}
        </div>
      ))}
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
    <Select value={value} onChange={(e) => onChange(e.target.value)} className="max-w-md">
      <option value="">— select a dataset —</option>
      {list.map((d) => (
        <option key={d.id} value={d.id}>
          {d.name} · {d.record_count} records
        </option>
      ))}
    </Select>
  );
}
