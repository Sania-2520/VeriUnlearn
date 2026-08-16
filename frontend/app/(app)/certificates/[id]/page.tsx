"use client";

import { use, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowLeft, Download, FileCheck2, ShieldCheck, BadgeCheck, XCircle, Braces } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge, statusTone } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/progress";

interface Certificate {
  id: string;
  subject_user_id: string;
  deletion_type: string;
  deleted_record_count: number;
  dataset_id: string | null;
  model_id: string | null;
  model_version: number;
  shard_ids: number[];
  pre_merkle_root: string;
  post_merkle_root: string;
  method: string;
  certified_bound: number | null;
  timestamp: string;
  content_hash: string;
  signature: string;
  verification_status: string;
  blockchain_tx: string | null;
  zk_proof: Record<string, unknown>;
}

export default function CertificatePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [verdict, setVerdict] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: cert, isLoading } = useQuery<Certificate>({
    queryKey: ["certificate", id],
    queryFn: () => api.get(`/api/v1/certificates/${id}`),
  });

  const verify = useMutation({
    mutationFn: () => api.post<Record<string, unknown>>(`/api/v1/verification/verify/${id}`),
    onSuccess: setVerdict,
    onError: (e) => setError(e instanceof ApiError ? e.message : "Verification failed"),
  });

  if (isLoading || !cert) {
    return <div className="flex justify-center py-16"><Spinner className="h-8 w-8" /></div>;
  }

  const rows: [string, string | number | null][] = [
    ["Certificate ID", cert.id],
    ["Subject user", cert.subject_user_id],
    ["Deletion type", cert.deletion_type],
    ["Method", cert.method],
    ["Deleted records", cert.deleted_record_count],
    ["Model version", cert.model_version],
    ["Shards", cert.shard_ids.join(", ") || "—"],
    ["Certified bound", cert.certified_bound !== null ? cert.certified_bound.toExponential(3) : "—"],
    ["Pre Merkle root", cert.pre_merkle_root],
    ["Post Merkle root", cert.post_merkle_root],
    ["Content hash (SHA-256)", cert.content_hash],
    ["Timestamp", cert.timestamp],
    ["Blockchain", cert.blockchain_tx ?? "local ledger"],
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link href="/certificates" className="text-slate-400 hover:text-cyan-300">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Certificate <span className="mono text-cyan-400">{cert.id.slice(0, 12)}</span></h1>
            <p className="mt-1 text-sm text-slate-500">
              <FileCheck2 className="mr-1 inline h-3.5 w-3.5" />
              Issued {new Date(cert.timestamp).toLocaleString()}
            </p>
          </div>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={() => api.download(`/api/v1/certificates/${cert.id}/download`, `certificate-${cert.id}.json`)}>
            <Download className="h-4 w-4" /> JSON
          </Button>
          <Button variant="outline" onClick={() => api.download(`/api/v1/certificates/${cert.id}/pdf`, `certificate-${cert.id}.pdf`)}>
            <Download className="h-4 w-4" /> PDF
          </Button>
          <Button onClick={() => verify.mutate()} loading={verify.isPending}>
            <ShieldCheck className="h-4 w-4" /> Verify
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">{error}</div>
      )}

      {verdict && (
        <Card className={verdict.verified ? "border-emerald-500/40" : "border-rose-500/40"}>
          <CardHeader>
            <CardTitle>Verification result</CardTitle>
            <Badge tone={verdict.verified ? "emerald" : "rose"}>
              {verdict.verified ? "verified" : "INVALID"}
            </Badge>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2 md:grid-cols-2">
              {Object.entries(verdict)
                .filter(([k]) => !["recomputed_post_root"].includes(k))
                .map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2 text-sm">
                    <span className="mono text-xs text-slate-500">{k}</span>
                    <span className="flex items-center gap-1.5 font-medium">
                      {v === true && <BadgeCheck className="h-4 w-4 text-emerald-400" />}
                      {v === false && <XCircle className="h-4 w-4 text-rose-400" />}
                      <span className={v === true ? "text-emerald-300" : v === false ? "text-rose-300" : "text-slate-200"}>
                        {typeof v === "boolean" ? (v ? "passed" : "failed") : String(v).slice(0, 40)}
                      </span>
                    </span>
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Certificate payload</CardTitle>
            <Badge tone={statusTone(cert.verification_status)}>{cert.verification_status}</Badge>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {rows.map(([k, v]) => (
                <div key={k} className="grid grid-cols-[160px_1fr] gap-3 rounded-lg border border-slate-800/60 bg-slate-900/30 px-3 py-2 text-sm">
                  <span className="mono text-xs uppercase tracking-wider text-slate-500">{k}</span>
                  <span className="mono break-all text-xs text-slate-200">{v}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Braces className="h-4 w-4 text-violet-400" /> ZK commitment proof
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="mono space-y-2 break-all text-xs text-slate-400">
                <p><span className="text-slate-500">scheme </span>{String(cert.zk_proof.scheme ?? "—")}</p>
                <p><span className="text-slate-500">commitment </span><span className="text-violet-300">{String(cert.zk_proof.commitment ?? "—").slice(0, 48)}…</span></p>
                <p><span className="text-slate-500">weights </span><span className="text-slate-500">hash only — never revealed</span></p>
                <p><span className="text-slate-500">records </span>{Array.isArray(cert.zk_proof.deleted_record_hashes) ? (cert.zk_proof.deleted_record_hashes as string[]).length : "—"} tombstoned</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Signature</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="mono break-all rounded-lg border border-slate-800 bg-slate-900/50 p-3 text-[11px] leading-relaxed text-slate-400">
                {cert.signature.slice(0, 160)}…
              </p>
              <p className="mt-3 text-xs text-slate-500">
                RSA-PKCS1v15 / SHA-256. Verify against the server public key or via the Verify API.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
