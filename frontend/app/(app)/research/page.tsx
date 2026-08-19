"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  FlaskConical,
  ShieldAlert,
  ShieldCheck,
  Gauge,
  Activity,
  ArrowRight,
  Microscope,
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/ui/stat";
import { Spinner } from "@/components/ui/progress";
import { timeAgo } from "@/lib/utils";

interface Experiment {
  id: string;
  name: string;
  version: number;
  seed: number;
  status: string;
  result_summary: Record<string, unknown> | null;
  created_at: string | null;
}

interface SecuritySummary {
  attack_count: number;
  summary: {
    mia_mean_auc: number | null;
    mia_max_leakage: number | null;
    poisoning_mean_persistence: number | null;
    extraction_mean_rate: number | null;
  };
  by_type: Record<string, number>;
}

interface PrivacyMatrix {
  metrics: string[];
  rows: { method: string; [k: string]: number | string }[];
  compliance: { readiness_score: number; status: string; gaps: string[] };
}

export default function ResearchDashboard() {
  const security = useQuery<SecuritySummary>({
    queryKey: ["metrics-security"],
    queryFn: () => api.get("/api/v1/metrics/security"),
  });
  const privacy = useQuery<PrivacyMatrix>({
    queryKey: ["metrics-privacy"],
    queryFn: () => api.get("/api/v1/metrics/privacy"),
  });
  const experiments = useQuery<{ experiments: Experiment[] }>({
    queryKey: ["experiments"],
    queryFn: () => api.get("/api/v1/experiments"),
  });
  const system = useQuery<{ live: { system_cpu_percent: number; system_ram_mb: number } }>({
    queryKey: ["metrics-system"],
    queryFn: () => api.get("/api/v1/metrics/system"),
  });

  const exps = experiments.data?.experiments ?? [];
  const sec = security.data?.summary;
  const privacyRows = privacy.data?.rows ?? [];
  const best = [...privacyRows].sort(
    (a, b) => (b.forget_quality_score as number) - (a.forget_quality_score as number)
  )[0];

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold tracking-tight">Research Hub</h1>
        <p className="mt-1 text-sm text-slate-500">
          Reproducible security evaluation, privacy benchmarking, and performance profiling — publication-grade experiments.
        </p>
      </motion.div>

      <div className="grid gap-4 md:grid-cols-4">
        <StatCard
          label="Experiments"
          value={exps.length}
          sub={exps.some((e) => e.status === "running") ? "one running" : "all archived"}
          icon={<FlaskConical className="h-4 w-4" />}
          accent="text-violet-400"
          delay={0}
        />
        <StatCard
          label="Attacks run"
          value={security.data?.attack_count ?? 0}
          sub="across 4 attack families"
          icon={<ShieldAlert className="h-4 w-4" />}
          accent="text-rose-400"
          delay={0.05}
        />
        <StatCard
          label="MIA leakage"
          value={sec?.mia_mean_auc != null ? `${((sec.mia_mean_auc - 0.5) * 200).toFixed(1)}%` : "—"}
          sub={sec?.mia_mean_auc != null ? `mean AUC ${sec.mia_mean_auc.toFixed(3)}` : "no MIA yet"}
          icon={<Activity className="h-4 w-4" />}
          accent="text-amber-400"
          delay={0.1}
        />
        <StatCard
          label="Compliance readiness"
          value={privacy.data ? `${(privacy.data.compliance.readiness_score * 100).toFixed(0)}%` : "—"}
          sub={privacy.data?.compliance.status ?? "no benchmark yet"}
          icon={<ShieldCheck className="h-4 w-4" />}
          accent="text-emerald-400"
          delay={0.15}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* best method + privacy matrix */}
        <Card>
          <CardHeader>
            <CardTitle>
              <span className="flex items-center gap-2"><Microscope className="h-4 w-4 text-cyan-400" /> Privacy matrix</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {privacy.isLoading ? (
              <div className="flex justify-center py-8"><Spinner /></div>
            ) : privacyRows.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-500">
                Run a benchmark to populate forget-quality, privacy-gain and retention metrics.
              </p>
            ) : (
              <div className="space-y-3">
                {best && (
                  <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-3 py-2 text-sm">
                    <span className="text-emerald-300">Best forget quality:</span>{" "}
                    <span className="font-semibold text-slate-100">{best.method}</span>{" "}
                    <span className="mono text-xs text-slate-400">
                      FQS {(best.forget_quality_score as number).toFixed(3)} · retention{" "}
                      {((best.knowledge_retention as number) * 100).toFixed(0)}%
                    </span>
                  </div>
                )}
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 text-[10px] uppercase tracking-wider text-slate-500">
                        <th className="py-2 pr-3">Method</th>
                        <th className="py-2 pr-3">Forget quality</th>
                        <th className="py-2 pr-3">Privacy gain</th>
                        <th className="py-2 pr-3">Retention</th>
                        <th className="py-2">Acc drop</th>
                      </tr>
                    </thead>
                    <tbody>
                      {privacyRows.map((r) => (
                        <tr key={r.method} className="border-b border-slate-800/50">
                          <td className="py-2 pr-3 font-medium text-slate-200">{r.method}</td>
                          <td className="mono py-2 pr-3 text-cyan-300">{(r.forget_quality_score as number).toFixed(3)}</td>
                          <td className="mono py-2 pr-3 text-emerald-300">{(r.privacy_gain as number).toFixed(3)}</td>
                          <td className="mono py-2 pr-3 text-slate-300">{((r.knowledge_retention as number) * 100).toFixed(0)}%</td>
                          <td className="mono py-2 text-amber-300">{((r.accuracy_drop as number) * 100).toFixed(1)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* security posture */}
        <Card>
          <CardHeader>
            <CardTitle>
              <span className="flex items-center gap-2"><ShieldAlert className="h-4 w-4 text-rose-400" /> Security posture</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-3">
                <p className="text-[10px] uppercase tracking-wider text-slate-500">MIA mean AUC</p>
                <p className="mono mt-1 text-lg font-semibold text-cyan-300">{sec?.mia_mean_auc?.toFixed(3) ?? "—"}</p>
              </div>
              <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-3">
                <p className="text-[10px] uppercase tracking-wider text-slate-500">Poison persistence</p>
                <p className="mono mt-1 text-lg font-semibold text-amber-300">{sec?.poisoning_mean_persistence?.toFixed(3) ?? "—"}</p>
              </div>
              <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-3">
                <p className="text-[10px] uppercase tracking-wider text-slate-500">Extraction rate</p>
                <p className="mono mt-1 text-lg font-semibold text-emerald-300">{sec?.extraction_mean_rate != null ? `${(sec.extraction_mean_rate * 100).toFixed(1)}%` : "—"}</p>
              </div>
              <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-3">
                <p className="text-[10px] uppercase tracking-wider text-slate-500">System CPU</p>
                <p className="mono mt-1 text-lg font-semibold text-slate-200">{system.data?.live.system_cpu_percent?.toFixed(1) ?? "—"}%</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {Object.entries(security.data?.by_type ?? {}).map(([k, v]) => (
                <Badge key={k} tone={v > 0 ? "violet" : "slate"}>{k} · {v}</Badge>
              ))}
            </div>
            <div className="flex flex-wrap gap-2 pt-1">
              <Link href="/research/attacks">
                <span className="flex items-center gap-1.5 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs font-medium text-rose-300 transition-colors hover:bg-rose-500/20">
                  Run attacks <ArrowRight className="h-3 w-3" />
                </span>
              </Link>
              <Link href="/research/benchmark">
                <span className="flex items-center gap-1.5 rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 text-xs font-medium text-cyan-300 transition-colors hover:bg-cyan-500/20">
                  Run benchmark <ArrowRight className="h-3 w-3" />
                </span>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* recent experiments */}
      <Card>
        <CardHeader>
          <CardTitle>
            <span className="flex items-center gap-2"><Gauge className="h-4 w-4 text-violet-400" /> Recent experiments</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {experiments.isLoading ? (
            <div className="flex justify-center py-8"><Spinner /></div>
          ) : exps.length === 0 ? (
            <p className="py-8 text-center text-sm text-slate-500">
              No experiments yet — create one in the Experiment Manager and run benchmarks against it.
            </p>
          ) : (
            <div className="space-y-2">
              {exps.slice(0, 6).map((e, i) => (
                <motion.div
                  key={e.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3"
                >
                  <span className={`h-2 w-2 rounded-full ${e.status === "completed" ? "bg-emerald-400" : e.status === "running" ? "bg-amber-400" : "bg-slate-600"}`} />
                  <span className="text-sm font-medium text-slate-200">{e.name}</span>
                  <Badge tone="slate">v{e.version}</Badge>
                  <Badge tone={e.status === "completed" ? "emerald" : "amber"}>{e.status}</Badge>
                  <span className="mono hidden text-xs text-slate-500 md:inline">seed {e.seed}</span>
                  <span className="ml-auto text-xs text-slate-500">{timeAgo(e.created_at)}</span>
                  <Link href={`/research/experiments/${e.id}`}>
                    <span className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 transition-colors hover:border-slate-500">
                      Open <ArrowRight className="ml-0.5 inline h-3 w-3" />
                    </span>
                  </Link>
                </motion.div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
