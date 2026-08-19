"use client";

import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  FileText,
  Hash,
  Layers,
  FileSearch,
  Database,
  Braces,
  FileBox,
  Cpu,
  Fingerprint,
  AlertTriangle,
} from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/progress";
import { shortHash } from "@/lib/utils";

interface RecordDetail {
  record_id: string;
  identity_key: string;
  full_name: string;
  email: string;
  phone: string;
  aadhaar: string;
  pan: string;
  passport: string;
  dob: string;
  address: string;
  original_text: string | null;
  metadata: Record<string, unknown>;
  label: string | null;
  file_name: string | null;
  dataset_id: string;
  dataset_name: string;
  timestamp: string | null;
  chat_id: string | null;
  chunk_index: number | null;
  chunk_id: string;
  embedding_id: string | null;
  vector_id: string | null;
  content_hash: string;
  shard_id: number;
  is_deleted: boolean;
  influence_score: number | null;
  sensitivity: string;
  pii_findings: {
    counts_by_severity: Record<string, number>;
    counts_by_category: Record<string, number>;
    risk_score: number;
  };
}

export default function RecordViewerPage() {
  const params = useSearchParams();
  const recordId = params.get("id") ?? "";

  const record = useQuery<RecordDetail>({
    queryKey: ["record", recordId],
    queryFn: () => api.get(`/api/v1/privacy/records/${recordId}`),
    enabled: !!recordId,
  });

  if (!recordId) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center text-slate-400">
        No record selected.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Record Viewer</h1>
          <p className="mt-1 text-sm text-slate-500">Full provenance of a single record — text, metadata, hashes, embeddings.</p>
        </div>
        <Link href="/privacy">
          <Button variant="outline">
            <ArrowLeft className="h-4 w-4" /> Back
          </Button>
        </Link>
      </motion.div>

      {record.isLoading ? (
        <div className="flex justify-center py-20">
          <Spinner className="h-8 w-8" />
        </div>
      ) : record.isError || !record.data ? (
        <div className="flex flex-col items-center gap-3 py-20 text-slate-400">
          <AlertTriangle className="h-8 w-8 text-rose-400" />
          <p>Record not found.</p>
        </div>
      ) : (
        (() => {
          const r = record.data;
          const rows = [
            { icon: FileBox, label: "File", value: r.file_name ?? "—" },
            { icon: Database, label: "Dataset", value: `${r.dataset_name} · v${r.dataset_id ? shortHash(r.dataset_id, 8) : ""}` },
            { icon: Layers, label: "Chunk", value: `${r.chunk_id} (index ${r.chunk_index ?? "—"})` },
            { icon: Braces, label: "Embedding", value: r.embedding_id ? shortHash(String(r.embedding_id), 14) : "—" },
            { icon: Cpu, label: "Vector", value: r.vector_id ? shortHash(String(r.vector_id), 14) : "—" },
            { icon: Hash, label: "SHA-256", value: shortHash(r.content_hash, 22) },
          ];
          return (
            <>
              <Card>
                <CardHeader>
                  <CardTitle>{r.full_name || "Anonymous record"}</CardTitle>
                  <Badge tone={r.is_deleted ? "rose" : r.sensitivity === "sensitive" ? "amber" : "emerald"}>
                    {r.is_deleted ? "deleted (tombstone)" : r.sensitivity}
                  </Badge>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {rows.map((row) => (
                      <div key={row.label} className="flex items-center gap-3 rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2.5">
                        <row.icon className="h-4 w-4 shrink-0 text-cyan-400" />
                        <div className="min-w-0">
                          <p className="text-[10px] uppercase tracking-wider text-slate-500">{row.label}</p>
                          <p className="mono truncate text-xs text-slate-300" title={row.value}>{row.value}</p>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
                    {[
                      ["Email", r.email], ["Phone", r.phone], ["Aadhaar", r.aadhaar], ["PAN", r.pan],
                      ["Passport", r.passport], ["DOB", r.dob], ["Chat", r.chat_id ?? "—"], ["Label", r.label ?? "—"],
                    ].map(([label, value]) => (
                      <div key={label} className="flex items-center justify-between rounded-lg border border-slate-800/60 px-3 py-2">
                        <span className="text-xs text-slate-500">{label}</span>
                        <span className="mono text-xs text-slate-300">{value || "—"}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>
                    <span className="flex items-center gap-2"><FileText className="h-4 w-4 text-cyan-400" /> Original content</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <pre className="max-h-72 overflow-auto rounded-lg border border-slate-800 bg-slate-950/60 p-4 text-xs leading-relaxed text-slate-300">
                    {r.original_text || JSON.stringify(r.metadata, null, 2)}
                  </pre>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>
                    <span className="flex items-center gap-2"><Fingerprint className="h-4 w-4 text-cyan-400" /> Metadata & PII findings</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-5 lg:grid-cols-2">
                    <div>
                      <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">Metadata</p>
                      <pre className="max-h-64 overflow-auto rounded-lg border border-slate-800 bg-slate-950/60 p-4 text-xs text-slate-300">
                        {JSON.stringify(r.metadata, null, 2)}
                      </pre>
                    </div>
                    <div>
                      <p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
                        <FileSearch className="h-3.5 w-3.5" /> PII analysis · risk {r.pii_findings.risk_score}/100
                      </p>
                      <div className="space-y-2">
                        <div className="grid grid-cols-4 gap-2">
                          {(["critical", "high", "medium", "low"] as const).map((sev) => (
                            <div key={sev} className="rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2 text-center">
                              <p className="text-lg font-bold text-slate-100">{r.pii_findings.counts_by_severity[sev] ?? 0}</p>
                              <p className="text-[10px] uppercase tracking-wider text-slate-500">{sev}</p>
                            </div>
                          ))}
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {Object.entries(r.pii_findings.counts_by_category).map(([cat, count]) => (
                            <Badge key={cat} tone="cyan" className="mono">{cat} × {count}</Badge>
                          ))}
                          {Object.keys(r.pii_findings.counts_by_category).length === 0 && (
                            <p className="text-xs text-slate-500">No PII detected.</p>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </>
          );
        })()
      )}
    </div>
  );
}
