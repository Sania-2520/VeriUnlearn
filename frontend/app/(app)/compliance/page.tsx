"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Scale, ShieldCheck, AlertTriangle, Timer, CheckCircle2, XCircle, Clock, FileBarChart, Download } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { StatCard } from "@/components/ui/stat";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge, statusTone } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Spinner } from "@/components/ui/progress";
import { formatSeconds } from "@/lib/utils";

type Overview = {
  gdpr: { score: number; status: string; details: { article_17_requests: number; resolution_rate: number; avg_deletion_seconds: number | null } };
  dpdp: { score: number; status: string; details: { consent_verification_rate: number } };
  risk: { score: number; level: string };
  requests: { total: number; completed: number; failed: number; pending: number; avg_deletion_seconds: number | null };
  certificates: { total: number; valid: number; invalid: number };
  audit_chain: { verified: boolean; event_count: number };
};

interface ComplianceReportRow {
  id: string;
  gdpr_score: number;
  gdpr_status: string;
  dpdp_score: number;
  dpdp_status: string;
  risk_score: number;
  risk_level: string;
  open_requests: number;
  completed_requests: number;
  created_at: string | null;
}

export default function CompliancePage() {
  const { data, isLoading } = useQuery<Overview>({
    queryKey: ["compliance-overview"],
    queryFn: () => api.get("/api/v1/compliance/overview"),
    refetchInterval: 30_000,
  });
  const reports = useQuery<{ reports: ComplianceReportRow[] }>({
    queryKey: ["compliance-reports"],
    queryFn: () => api.get("/api/v1/compliance/reports"),
  });
  const qc = useQueryClient();
  const generate = useMutation({
    mutationFn: () => api.post("/api/v1/compliance/report"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["compliance-reports"] }),
  });
  const download = (format: string) => {
    const a = document.createElement("a");
    a.href = `/api/v1/compliance/export?format=${format}`;
    a.download = `veriunlearn-compliance.${format}`;
    a.click();
  };

  if (isLoading || !data) {
    return <div className="flex justify-center py-16"><Spinner className="h-8 w-8" /></div>;
  }

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold tracking-tight">Compliance</h1>
        <p className="mt-1 text-sm text-slate-500">Live GDPR Article 17 and DPDP Act 2023 posture.</p>
      </motion.div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="GDPR Art. 17" value={data.gdpr.score} sub={data.gdpr.status} icon={<Scale className="h-5 w-5" />} accent="text-emerald-400" />
        <StatCard label="DPDP Act 2023" value={data.dpdp.score} sub={data.dpdp.status} icon={<ShieldCheck className="h-5 w-5" />} accent="text-cyan-400" />
        <StatCard label="Risk score" value={data.risk.score} sub={`${data.risk.level}`} icon={<AlertTriangle className="h-5 w-5" />} accent={data.risk.level === "low" ? "text-emerald-400" : data.risk.level === "medium" ? "text-amber-400" : "text-rose-400"} />
        <StatCard label="Avg deletion time" value={formatSeconds(data.requests.avg_deletion_seconds)} icon={<Timer className="h-5 w-5" />} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>GDPR Article 17 — Right to erasure</CardTitle>
            <Badge tone={statusTone(data.gdpr.status)}>{data.gdpr.status}</Badge>
          </CardHeader>
          <CardContent>
            <Progress value={data.gdpr.score} className="mb-5 h-2.5" />
            <div className="space-y-3">
              <Metric label="Requests received" value={data.requests.total} />
              <Metric label="Resolution rate" value={`${(data.gdpr.details.resolution_rate * 100).toFixed(1)}%`} />
              <Metric label="Average response time" value={formatSeconds(data.gdpr.details.avg_deletion_seconds)} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>DPDP Act 2023 — Consent framework</CardTitle>
            <Badge tone={statusTone(data.dpdp.status)}>{data.dpdp.status}</Badge>
          </CardHeader>
          <CardContent>
            <Progress value={data.dpdp.score} className="mb-5 h-2.5" />
            <div className="space-y-3">
              <Metric label="Consent lifecycle verification" value={`${(data.dpdp.details.consent_verification_rate * 100).toFixed(1)}%`} />
              <Metric label="Data principal requests" value={data.requests.total} />
              <Metric label="Erasure completed" value={data.requests.completed} />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-400" /> Completed</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-emerald-300">{data.requests.completed}</p>
            <p className="mt-1 text-xs text-slate-500">of {data.requests.total} requests</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Clock className="h-4 w-4 text-amber-400" /> Pending</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-amber-300">{data.requests.pending}</p>
            <p className="mt-1 text-xs text-slate-500">in flight</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><XCircle className="h-4 w-4 text-rose-400" /> Failed / Invalid</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-rose-300">{data.requests.failed + data.certificates.invalid}</p>
            <p className="mt-1 text-xs text-slate-500">{data.certificates.invalid} invalid certificates</p>
          </CardContent>
        </Card>
      </div>

      {/* Phase 7 — persisted compliance reports */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2"><FileBarChart className="h-4 w-4 text-violet-400" /> Compliance reports</span>
            <span className="flex items-center gap-2">
              <Button size="sm" onClick={() => generate.mutate()} loading={generate.isPending}>
                <FileBarChart className="h-3.5 w-3.5" /> Generate snapshot
              </Button>
              <Button variant="outline" size="sm" onClick={() => download("csv")}><Download className="h-3.5 w-3.5" /> CSV</Button>
              <Button variant="outline" size="sm" onClick={() => download("json")}><Download className="h-3.5 w-3.5" /> JSON</Button>
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {reports.isLoading ? (
            <div className="flex justify-center py-6"><Spinner /></div>
          ) : (reports.data?.reports ?? []).length === 0 ? (
            <p className="py-6 text-center text-sm text-slate-500">No snapshots yet — generate one to trend compliance over time.</p>
          ) : (
            <div className="max-h-72 space-y-1.5 overflow-auto">
              {(reports.data?.reports ?? []).slice(0, 50).map((r, i) => (
                <motion.div
                  key={r.id}
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: Math.min(i * 0.02, 0.4) }}
                  className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-800/70 bg-slate-900/30 px-3 py-2 text-xs"
                >
                  <Badge tone={statusTone(r.gdpr_status)}>GDPR {r.gdpr_score.toFixed(0)}</Badge>
                  <Badge tone={statusTone(r.dpdp_status)}>DPDP {r.dpdp_score.toFixed(0)}</Badge>
                  <Badge tone={r.risk_level === "low" ? "emerald" : r.risk_level === "medium" ? "amber" : "rose"}>risk {r.risk_score.toFixed(0)}</Badge>
                  <span className="mono text-slate-500">{r.completed_requests} done / {r.open_requests} open</span>
                  <span className="ml-auto text-slate-500">{r.created_at ? new Date(r.created_at).toLocaleString() : "—"}</span>
                </motion.div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2.5 text-sm">
      <span className="text-slate-400">{label}</span>
      <span className="mono font-semibold text-cyan-300">{value}</span>
    </div>
  );
}
