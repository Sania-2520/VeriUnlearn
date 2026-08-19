"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  ShieldAlert,
  ArrowLeft,
  FileSearch,
  Database,
  Layers,
  Clock,
  AlertTriangle,
} from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/ui/stat";
import { Spinner } from "@/components/ui/progress";
import { Table, THead, Th, Td, TRow } from "@/components/ui/table";
import { timeAgo } from "@/lib/utils";

interface Finding {
  record_id: string;
  identity_key: string;
  full_name: string;
  dataset_id: string;
  shard_id: number;
  category: string;
  severity: string;
  snippet: string;
  confidence: number;
  field: string | null;
}

interface Report {
  id: string;
  scope: string;
  subject: string | null;
  dataset_id: string | null;
  scanned_records: number;
  findings_count: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  categories: Record<string, number>;
  risk_score: number;
  findings: Finding[];
  created_at: string | null;
}

const severityTone: Record<string, "rose" | "amber" | "cyan" | "slate" | "emerald"> = {
  critical: "rose",
  high: "amber",
  medium: "cyan",
  low: "slate",
};

export default function PrivacyReportPage() {
  const params = useParams<{ id: string }>();
  const report = useQuery<Report>({
    queryKey: ["privacy-report", params.id],
    queryFn: () => api.get(`/api/v1/privacy/report/${params.id}`),
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
        <AlertTriangle className="h-8 w-8 text-rose-400" />
        <p>Report not found.</p>
        <Link href="/privacy">
          <Button variant="outline">
            <ArrowLeft className="h-4 w-4" /> Back to Privacy Auditor
          </Button>
        </Link>
      </div>
    );
  }

  const r = report.data;
  const severityBar = [
    { label: "Critical", count: r.critical_count, color: "bg-rose-500" },
    { label: "High", count: r.high_count, color: "bg-amber-500" },
    { label: "Medium", count: r.medium_count, color: "bg-cyan-500" },
    { label: "Low", count: r.low_count, color: "bg-slate-500" },
  ];

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Privacy Report</h1>
          <p className="mt-1 text-sm text-slate-500">
            {r.scope} scan{r.subject ? ` · subject: ${r.subject}` : ""} · {timeAgo(r.created_at)}
          </p>
        </div>
        <Link href="/privacy">
          <Button variant="outline">
            <ArrowLeft className="h-4 w-4" /> Back
          </Button>
        </Link>
      </motion.div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Records scanned" value={r.scanned_records} icon={<Database className="h-4 w-4" />} accent="text-cyan-400" />
        <StatCard label="Findings" value={r.findings_count} icon={<FileSearch className="h-4 w-4" />} accent="text-violet-400" />
        <StatCard
          label="Risk score"
          value={`${r.risk_score}/100`}
          icon={<ShieldAlert className="h-4 w-4" />}
          accent={r.risk_score >= 60 ? "text-rose-400" : r.risk_score >= 30 ? "text-amber-400" : "text-emerald-400"}
        />
        <StatCard label="Categories" value={Object.keys(r.categories).length} icon={<Layers className="h-4 w-4" />} accent="text-emerald-400" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Severity distribution</CardTitle>
          <Clock className="h-5 w-5 text-cyan-400" />
        </CardHeader>
        <CardContent>
          <div className="flex h-3 w-full overflow-hidden rounded-full bg-slate-800">
            {severityBar.map((s) =>
              s.count > 0 ? (
                <div
                  key={s.label}
                  className={s.color}
                  style={{ width: `${(s.count / Math.max(r.findings_count, 1)) * 100}%` }}
                  title={`${s.label}: ${s.count}`}
                />
              ) : null
            )}
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {severityBar.map((s) => (
              <div key={s.label} className="rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2">
                <p className="text-[11px] uppercase tracking-wider text-slate-500">{s.label}</p>
                <p className="mt-1 text-xl font-bold text-slate-100">{s.count}</p>
              </div>
            ))}
          </div>
          {Object.keys(r.categories).length > 0 && (
            <div className="mt-5 flex flex-wrap gap-2">
              {Object.entries(r.categories)
                .sort((a, b) => b[1] - a[1])
                .map(([cat, count]) => (
                  <Badge key={cat} tone="cyan" className="mono">
                    {cat} × {count}
                  </Badge>
                ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Findings — {r.findings.length} stored (aggregates are exact)</CardTitle>
          <ShieldAlert className="h-5 w-5 text-rose-400" />
        </CardHeader>
        <Table>
          <THead>
            <tr>
              <Th>Category</Th>
              <Th>Severity</Th>
              <Th>Snippet</Th>
              <Th>Field</Th>
              <Th>Confidence</Th>
              <Th>Shard</Th>
            </tr>
          </THead>
          <tbody>
            {r.findings.map((f, i) => (
              <TRow key={i}>
                <Td>
                  <span className="mono text-xs text-slate-300">{f.category}</span>
                </Td>
                <Td>
                  <Badge tone={severityTone[f.severity] ?? "slate"}>{f.severity}</Badge>
                </Td>
                <Td className="max-w-md">
                  <span className="mono block truncate text-xs text-slate-400" title={f.snippet}>
                    {f.snippet}
                  </span>
                </Td>
                <Td className="mono text-xs text-slate-500">{f.field ?? "—"}</Td>
                <Td className="text-xs text-slate-400">{(f.confidence * 100).toFixed(0)}%</Td>
                <Td className="mono text-xs">{f.shard_id}</Td>
              </TRow>
            ))}
          </tbody>
        </Table>
      </Card>
    </div>
  );
}
