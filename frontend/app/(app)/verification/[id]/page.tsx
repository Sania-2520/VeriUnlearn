"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  ShieldCheck,
  ShieldAlert,
  ArrowLeft,
  FileCheck2,
  GitBranch,
  KeyRound,
  ScrollText,
  CheckCircle2,
  XCircle,
  Timer,
  Database,
  Download,
} from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/ui/stat";
import { Spinner } from "@/components/ui/progress";

interface Check {
  passed: boolean;
  details: Record<string, unknown>;
}

interface Report {
  id: string;
  certificate_id: string;
  deletion_request_id: string | null;
  dataset_id: string | null;
  model_id: string | null;
  verdict: string;
  checks_passed: number;
  checks_total: number;
  checks: Record<string, Check>;
  merkle_snapshot: {
    root: string;
    leaf_count: number;
    levels_depth: number;
    levels?: { depth: number; node_count: number; nodes: string[]; truncated: boolean }[];
  };
  duration_seconds: number | null;
  created_by: string;
  created_at: string | null;
}

const CHECK_ICONS: Record<string, { icon: typeof Database; color: string }> = {
  records: { icon: Database, color: "text-cyan-400" },
  embeddings: { icon: Database, color: "text-violet-400" },
  vectors: { icon: Database, color: "text-emerald-400" },
  versions: { icon: FileCheck2, color: "text-amber-400" },
  merkle: { icon: GitBranch, color: "text-cyan-400" },
  signature: { icon: KeyRound, color: "text-amber-400" },
  audit: { icon: ScrollText, color: "text-violet-400" },
  consistency: { icon: Database, color: "text-emerald-400" },
};

export default function VerificationReportPage() {
  const params = useParams<{ id: string }>();
  const report = useQuery<Report>({
    queryKey: ["verification-report", params.id],
    queryFn: () => api.get(`/api/v1/verification/${params.id}`),
  });

  if (report.isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }
  if (report.isError || !report.data) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 text-slate-400">
        <ShieldAlert className="h-8 w-8 text-rose-400" />
        <p>Verification report not found.</p>
        <Link href="/verification">
          <Button variant="outline">
            <ArrowLeft className="h-4 w-4" /> Back to Verification
          </Button>
        </Link>
      </div>
    );
  }

  const r = report.data;
  const valid = r.verdict === "valid";
  const entries = Object.entries(r.checks);

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Verification Report</h1>
          <p className="mono mt-1 text-sm text-slate-500">{r.id}</p>
        </div>
        <div className="flex items-center gap-3">
          <Badge tone={valid ? "emerald" : "rose"} className="px-3 py-1.5 text-sm">
            {valid ? <ShieldCheck className="mr-1 h-4 w-4" /> : <ShieldAlert className="mr-1 h-4 w-4" />}
            {valid ? "VALID" : "INVALID"}
          </Badge>
          <Link href={`/certificates/${r.certificate_id}`}>
            <Button variant="outline">
              <FileCheck2 className="h-4 w-4" /> Certificate
            </Button>
          </Link>
          <Button
            variant="outline"
            onClick={() => api.download(`/api/v1/verification/download/json/${r.id}`, `verification-${r.id}.json`)}
          >
            <Download className="h-4 w-4" /> JSON
          </Button>
          <Button
            variant="outline"
            onClick={() => api.download(`/api/v1/verification/download/pdf/${r.id}`, `verification-${r.id}.pdf`)}
          >
            <Download className="h-4 w-4" /> PDF
          </Button>
        </div>
      </motion.div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Checks passed"
          value={`${r.checks_passed}/${r.checks_total}`}
          icon={<ShieldCheck className="h-4 w-4" />}
          accent={valid ? "text-emerald-400" : "text-rose-400"}
        />
        <StatCard label="Duration" value={r.duration_seconds ? `${r.duration_seconds}s` : "—"} icon={<Timer className="h-4 w-4" />} accent="text-cyan-400" />
        <StatCard label="Merkle leaves" value={r.merkle_snapshot.leaf_count} icon={<GitBranch className="h-4 w-4" />} accent="text-violet-400" />
        <StatCard label="Tree depth" value={r.merkle_snapshot.levels_depth} icon={<Database className="h-4 w-4" />} accent="text-amber-400" />
      </div>

      {/* per-check breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>Check breakdown</CardTitle>
          <FileCheck2 className="h-5 w-5 text-cyan-400" />
        </CardHeader>
        <CardContent className="space-y-3">
          {entries.map(([name, check], i) => {
            const meta = CHECK_ICONS[name] ?? { icon: Database, color: "text-slate-400" };
            const Icon = meta.icon;
            return (
              <motion.div
                key={name}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="flex flex-wrap items-start gap-3 rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3"
              >
                <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${meta.color}`} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold capitalize text-slate-200">{name}</span>
                    {check.passed ? (
                      <Badge tone="emerald"><CheckCircle2 className="mr-1 h-3 w-3" /> PASS</Badge>
                    ) : (
                      <Badge tone="rose"><XCircle className="mr-1 h-3 w-3" /> FAIL</Badge>
                    )}
                  </div>
                  <pre className="mono mt-2 max-h-24 overflow-auto rounded-lg bg-slate-950/50 p-2 text-[11px] text-slate-400">
                    {JSON.stringify(check.details, null, 2)}
                  </pre>
                </div>
              </motion.div>
            );
          })}
        </CardContent>
      </Card>

      {/* merkle tree visualization */}
      <Card>
        <CardHeader>
          <CardTitle>
            <span className="flex items-center gap-2"><GitBranch className="h-4 w-4 text-cyan-400" /> Merkle tree</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="mono text-xs text-slate-500">root</span>
            <code className="mono rounded bg-slate-950/60 px-2 py-1 text-xs text-cyan-300">{r.merkle_snapshot.root}</code>
          </div>
          <MerkleTreeViz levels={r.merkle_snapshot.levels ?? []} />
        </CardContent>
      </Card>
    </div>
  );
}

function MerkleTreeViz({ levels }: { levels: { depth: number; node_count: number; nodes: string[]; truncated: boolean }[] }) {
  if (levels.length === 0) {
    return <p className="text-sm text-slate-500">No tree snapshot stored for this report.</p>;
  }
  return (
    <div className="space-y-2">
      {[...levels].reverse().map((level) => (
        <div key={level.depth} className="flex items-center gap-1.5 overflow-x-auto pb-1">
          <span className="mono w-10 shrink-0 text-[10px] text-slate-600">L{level.depth}</span>
          <div className="flex items-center gap-1.5">
            {level.nodes.slice(0, 24).map((node, i) => (
              <div
                key={i}
                title={node}
                className={`h-3.5 w-3.5 shrink-0 rounded-sm ${
                  level.depth === levels.length - 1 ? "bg-cyan-400/70" : level.depth === 0 ? "bg-emerald-400/80" : "bg-violet-400/50"
                }`}
              />
            ))}
            {level.truncated && <span className="mono shrink-0 text-[10px] text-slate-600">+{level.node_count - 24}</span>}
          </div>
          <span className="mono shrink-0 text-[10px] text-slate-600">×{level.node_count}</span>
        </div>
      ))}
      <div className="flex gap-4 pt-2 text-[11px] text-slate-500">
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-sm bg-cyan-400/70" /> leaves</span>
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-sm bg-violet-400/50" /> internal</span>
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-sm bg-emerald-400/80" /> root</span>
      </div>
    </div>
  );
}
