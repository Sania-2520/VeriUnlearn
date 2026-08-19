"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Fingerprint, Eye, Bug, FileX2, Play } from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
} from "recharts";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select } from "@/components/ui/select";
import { Table, THead, Th, Td, TRow } from "@/components/ui/table";

interface MLModel {
  id: string;
  name: string;
  version: number;
  status: string;
  metrics: Record<string, number>;
}

interface Result {
  [k: string]: unknown;
}

function num(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

function num0(v: unknown): number {
  return num(v) ?? 0;
}

export default function ResearchAttacksPage() {
  const qc = useQueryClient();
  const [modelId, setModelId] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [mia, setMia] = useState<Result | null>(null);
  const [inversion, setInversion] = useState<Result | null>(null);
  const [extraction, setExtraction] = useState<Result | null>(null);
  const [poisoning, setPoisoning] = useState<Result | null>(null);
  const [poisonType, setPoisonType] = useState("backdoor");

  const models = useQuery<MLModel[]>({
    queryKey: ["models"],
    queryFn: () => api.get("/api/v1/models?limit=50"),
  });
  const readyModels = (models.data ?? []).filter((m) => m.status === "ready");

  function fail(e: unknown) {
    setNotice(e instanceof ApiError ? e.message : "Attack failed");
  }

  const runMia = useMutation({
    mutationFn: () => api.post<Result>("/api/v1/attack/mia", { model_id: modelId }),
    onSuccess: (d) => { setMia(d); setNotice(null); void qc.invalidateQueries({ queryKey: ["metrics-security"] }); },
    onError: fail,
  });
  const runInversion = useMutation({
    mutationFn: () => api.post<Result>("/api/v1/attack/inversion", { model_id: modelId }),
    onSuccess: (d) => { setInversion(d); setNotice(null); void qc.invalidateQueries({ queryKey: ["metrics-security"] }); },
    onError: fail,
  });
  const runExtraction = useMutation({
    mutationFn: () => api.post<Result>("/api/v1/attack/extraction", { model_id: modelId, deleted_record_ids: [] }),
    onSuccess: (d) => { setExtraction(d); setNotice(null); void qc.invalidateQueries({ queryKey: ["metrics-security"] }); },
    onError: fail,
  });
  const runPoisoning = useMutation({
    mutationFn: () =>
      api.post<Result>("/api/v1/attack/poisoning", { model_id: modelId, attack_type: poisonType }),
    onSuccess: (d) => { setPoisoning(d); setNotice(null); void qc.invalidateQueries({ queryKey: ["metrics-security"] }); },
    onError: fail,
  });

  const stages = (mia?.stages as Record<string, Result> | undefined) ?? {};
  const stageNames = Object.keys(stages);
  const stageChart = stageNames.map((s) => {
    const auc = num(stages[s]?.auc) ?? 0;
    return { name: s, auc: +auc.toFixed(3), fill: auc > 0.7 ? "#f87171" : "#34d399" };
  });

  const poisonChart = [
    {
      name: "Trigger before",
      value: +(num(poisoning?.trigger_fires_before_unlearning) ?? 0).toFixed(3),
      fill: "#f59e0b",
    },
    {
      name: "Trigger after",
      value: +(num(poisoning?.trigger_fires_after_unlearning) ?? 0).toFixed(3),
      fill: "#22d3ee",
    },
    {
      name: "Persistence",
      value: +(num(poisoning?.persistence_ratio) ?? 0).toFixed(3),
      fill: (num(poisoning?.persistence_ratio) ?? 0) > 0.5 ? "#f87171" : "#34d399",
    },
    {
      name: "Removal success",
      value: +(num(poisoning?.removal_success) ?? 0).toFixed(3),
      fill: "#34d399",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Attack Suite</h1>
          <p className="mt-1 text-sm text-slate-500">
            Four attack families probing residual leakage before and after unlearning.
          </p>
        </div>
        <Select value={modelId} onChange={(e) => setModelId(e.target.value)} className="w-72">
          <option value="">Select a trained model…</option>
          {readyModels.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name} · v{m.version} · acc {((m.metrics.accuracy ?? 0) * 100).toFixed(1)}%
            </option>
          ))}
        </Select>
      </div>

      {notice && <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">{notice}</div>}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Fingerprint className="h-4 w-4 text-cyan-400" /> Membership inference</CardTitle>
            <Badge tone={mia ? (stageNames.length > 1 ? "violet" : "slate") : "slate"}>
              {stageNames.length > 1 ? `${stageNames.length} stages` : mia ? "original only" : "not run"}
            </Badge>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm leading-relaxed text-slate-400">
              Can an attacker tell which records were in training? Reports AUC, precision/recall, privacy leakage and
              membership confidence per stage (original → post-unlearning → post-verification).
            </p>
            {mia && (
              <>
                <div className="grid grid-cols-2 gap-3">
                  <Metric label="Sample size" value={String(num(mia.sample_size) ?? "—")} />
                  <Metric label="Mean AUC" value={stageNames.length ? num(stages[stageNames[0]].auc ?? 0)?.toFixed(3) ?? "—" : "—"} />
                  <Metric label="Privacy leakage" value={num(mia.privacy_leakage)?.toFixed(3) ?? "—"} />
                  <Metric label="Membership conf." value={num(mia.membership_confidence)?.toFixed(3) ?? "—"} />
                </div>
                {stageChart.length > 1 && (
                  <ResponsiveContainer width="100%" height={180}>
                    <BarChart data={stageChart}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="name" stroke="#64748b" fontSize={11} />
                      <YAxis stroke="#64748b" fontSize={11} domain={[0, 1]} />
                      <Tooltip contentStyle={{ background: "#0a0f1c", border: "1px solid #1e293b", borderRadius: 8 }} />
                      <Bar dataKey="auc" name="AUC" radius={[5, 5, 0, 0]}>
                        {stageChart.map((d, i) => <Cell key={i} fill={d.fill} />)}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </>
            )}
            <Button className="w-full" size="sm" disabled={!modelId} onClick={() => runMia.mutate()} loading={runMia.isPending}>
              <Fingerprint className="h-3.5 w-3.5" /> Run MIA
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Eye className="h-4 w-4 text-violet-400" /> Model inversion</CardTitle>
            <Badge tone={inversion ? "slate" : "slate"}>{inversion ? "measured" : "not run"}</Badge>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm leading-relaxed text-slate-400">
              Gradient ascent on input space attempts to reconstruct a prototypical member of the target class.
              Lower reconstruction error = more information leakage.
            </p>
            {inversion && (
              <div className="grid grid-cols-2 gap-3">
                <Metric label="Target class" value={String(num(inversion.target_label) ?? "—")} />
                <Metric label="Reconstruction error" value={num(inversion.reconstruction_error)?.toExponential(2) ?? "—"} />
                <Metric label="Information leakage" value={num(inversion.information_leakage)?.toFixed(3) ?? "—"} />
                <Metric label="Similarity score" value={num(inversion.similarity_score)?.toFixed(3) ?? "—"} />
              </div>
            )}
            <Button className="w-full" size="sm" disabled={!modelId} onClick={() => runInversion.mutate()} loading={runInversion.isPending}>
              <Eye className="h-3.5 w-3.5" /> Run inversion
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><FileX2 className="h-4 w-4 text-amber-400" /> Data extraction</CardTitle>
            <Badge tone={extraction ? "slate" : "slate"}>{extraction ? "measured" : "not run"}</Badge>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm leading-relaxed text-slate-400">
              Probes whether deleted knowledge is still recoverable — embeddings, vectors, metadata, and served text
              of tombstoned records.
            </p>
            {extraction && (
              <div className="grid grid-cols-2 gap-3">
                <Metric label="Extraction success" value={num(extraction.extraction_success_rate) != null ? `${(num(extraction.extraction_success_rate)! * 100).toFixed(1)}%` : "—"} />
                <Metric label="Records checked" value={String(num(extraction.checked) ?? "—")} />
                <Metric label="Embeddings recovered" value={String(num(extraction.embedding_recovered) ?? "—")} />
                <Metric label="Vectors recovered" value={String(num(extraction.vector_recovered) ?? "—")} />
              </div>
            )}
            <Button className="w-full" size="sm" disabled={!modelId} onClick={() => runExtraction.mutate()} loading={runExtraction.isPending}>
              <FileX2 className="h-3.5 w-3.5" /> Run extraction test
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Bug className="h-4 w-4 text-rose-400" /> Poisoning resistance</CardTitle>
            <Badge tone={poisoning ? (num0(poisoning.persistence_ratio) > 0.5 ? "rose" : "emerald") : "slate"}>
              {poisoning ? (num0(poisoning.persistence_ratio) > 0.5 ? "persists" : "purged") : "not run"}
            </Badge>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm leading-relaxed text-slate-400">
              Simulate backdoor / label-flip / gradient poisoning, unlearn the poisoned rows, and measure whether the
              trigger still fires.
            </p>
            <div className="flex items-center gap-2">
              <Select value={poisonType} onChange={(e) => setPoisonType(e.target.value)} className="w-40">
                <option value="backdoor">backdoor</option>
                <option value="label_flip">label flip</option>
                <option value="gradient">gradient</option>
              </Select>
              <Button size="sm" disabled={!modelId} onClick={() => runPoisoning.mutate()} loading={runPoisoning.isPending}>
                <Bug className="h-3.5 w-3.5" /> Run poisoning
              </Button>
            </div>
            {poisoning && (
              <>
                <div className="grid grid-cols-3 gap-3">
                  <Metric label="Poisoned rows" value={String(num(poisoning.poisoned_records) ?? "—")} />
                  <Metric label="Detection rate" value={num(poisoning.detection_rate)?.toFixed(3) ?? "—"} />
                  <Metric label="Robustness" value={num(poisoning.robustness_score)?.toFixed(3) ?? "—"} />
                </div>
                <ResponsiveContainer width="100%" height={160}>
                  <BarChart data={poisonChart}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
                    <YAxis stroke="#64748b" fontSize={11} domain={[0, 1]} />
                    <Tooltip contentStyle={{ background: "#0a0f1c", border: "1px solid #1e293b", borderRadius: 8 }} />
                    <Bar dataKey="value" radius={[5, 5, 0, 0]}>
                      {poisonChart.map((d, i) => <Cell key={i} fill={d.fill} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {(mia || inversion || extraction || poisoning) && (
        <Card>
          <CardHeader><CardTitle>Run summary</CardTitle></CardHeader>
          <CardContent>
            <Table>
              <THead>
                <tr>
                  <Th>Attack</Th>
                  <Th>Key metric</Th>
                  <Th>Verdict</Th>
                </tr>
              </THead>
              <tbody>
                <TRow>
                  <Td className="font-medium text-slate-100">Membership inference</Td>
                  <Td className="mono">AUC {stageNames.length ? num(stages[stageNames[0]].auc ?? 0)?.toFixed(3) : "—"}</Td>
                  <Td>
                    <Badge tone={num0(stages[stageNames[0]]?.auc) > 0.7 ? "rose" : "emerald"}>
                      {num0(stages[stageNames[0]]?.auc) > 0.7 ? "at risk" : "resilient"}
                    </Badge>
                  </Td>
                </TRow>
                <TRow>
                  <Td className="font-medium text-slate-100">Model inversion</Td>
                  <Td className="mono">{num(inversion?.similarity_score)?.toFixed(3) ?? "—"} similarity</Td>
                  <Td><Badge tone="slate">{inversion ? "measured" : "not run"}</Badge></Td>
                </TRow>
                <TRow>
                  <Td className="font-medium text-slate-100">Data extraction</Td>
                  <Td className="mono">
                    {num(extraction?.extraction_success_rate) != null ? `${(num(extraction!.extraction_success_rate)! * 100).toFixed(1)}%` : "—"}
                  </Td>
                  <Td>
                    <Badge tone={num0(extraction?.extraction_success_rate) > 0 ? "rose" : "emerald"}>
                      {num0(extraction?.extraction_success_rate) > 0 ? "leaking" : "clean"}
                    </Badge>
                  </Td>
                </TRow>
                <TRow>
                  <Td className="font-medium text-slate-100">Poisoning ({poisonType})</Td>
                  <Td className="mono">persistence {num(poisoning?.persistence_ratio)?.toFixed(3) ?? "—"}</Td>
                  <Td>
                    <Badge tone={num0(poisoning?.persistence_ratio) > 0.5 ? "rose" : "emerald"}>
                      {num0(poisoning?.persistence_ratio) > 0.5 ? "persists" : "purged"}
                    </Badge>
                  </Td>
                </TRow>
              </tbody>
            </Table>
            <p className="mt-3 flex items-center gap-1.5 text-xs text-slate-500">
              <Play className="h-3 w-3" /> Pass <code className="mono rounded bg-slate-800 px-1 py-0.5">deleted_record_ids</code> to MIA/extraction to
              compare post-unlearning stages.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-3">
      <p className="text-[10px] uppercase tracking-wider text-slate-500">{label}</p>
      <p className="mono mt-1 text-lg font-semibold text-cyan-300">{value}</p>
    </div>
  );
}
