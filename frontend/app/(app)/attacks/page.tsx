"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Crosshair, Bug, Fingerprint, Eye, Flame } from "lucide-react";
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

interface MLModel {
  id: string;
  name: string;
  version: number;
  status: string;
  metrics: Record<string, number>;
}

export default function AttacksPage() {
  const [modelId, setModelId] = useState<string>("");
  const [notice, setNotice] = useState<string | null>(null);
  const [mia, setMia] = useState<Record<string, unknown> | null>(null);
  const [backdoor, setBackdoor] = useState<Record<string, unknown> | null>(null);
  const [inversion, setInversion] = useState<Record<string, unknown> | null>(null);

  const { data: models } = useQuery<MLModel[]>({
    queryKey: ["models"],
    queryFn: () => api.get("/api/v1/models?limit=50"),
  });

  const readyModels = (models ?? []).filter((m) => m.status === "ready");

  function fail(e: unknown) {
    setNotice(e instanceof ApiError ? e.message : "Attack failed");
  }

  const runMia = useMutation({
    mutationFn: () => api.post<Record<string, unknown>>(`/api/v1/attacks/membership/${modelId}`),
    onSuccess: (d) => { setMia(d); setNotice(null); },
    onError: fail,
  });
  const runBackdoor = useMutation({
    mutationFn: () => api.post<Record<string, unknown>>(`/api/v1/attacks/backdoor/${modelId}?poison_fraction=0.2`),
    onSuccess: (d) => { setBackdoor(d); setNotice(null); },
    onError: fail,
  });
  const runInversion = useMutation({
    mutationFn: () => api.post<Record<string, unknown>>(`/api/v1/attacks/inversion/${modelId}`),
    onSuccess: (d) => { setInversion(d); setNotice(null); },
    onError: fail,
  });

  const chartData = [
    { name: "MIA AUC", value: mia ? Number(mia.auc) : 0, fill: mia && Number(mia.auc) > 0.7 ? "#f87171" : "#34d399" },
    { name: "Backdoor persistence", value: backdoor ? Number(backdoor.persistence_ratio) : 0, fill: backdoor && Number(backdoor.persistence_ratio) > 0.5 ? "#f87171" : "#34d399" },
    { name: "Inversion error", value: inversion ? Number(inversion.reconstruction_error) : 0, fill: inversion && Number(inversion.reconstruction_error) > 0.5 ? "#fbbf24" : "#34d399" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Attack Lab</h1>
          <p className="mt-1 text-sm text-slate-500">
            Probe residual privacy leakage: membership inference, backdoor persistence, model inversion.
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

      {notice && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">{notice}</div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Fingerprint className="h-4 w-4 text-cyan-400" /> Membership inference</CardTitle>
            <Badge tone={mia ? (Number(mia.auc) > 0.7 ? "rose" : "emerald") : "slate"}>
              {mia ? (Number(mia.auc) > 0.7 ? "at risk" : "resilient") : "not run"}
            </Badge>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed text-slate-400">
              Can an attacker tell which records were in training? Measured by confidence-separation AUC
              on a held-out split.
            </p>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <Metric label="AUC" value={mia ? Number(mia.auc).toFixed(3) : "—"} />
              <Metric label="Attack success" value={mia ? `${(Number(mia.attack_success_rate) * 100).toFixed(1)}%` : "—"} />
              <Metric label="Train conf." value={mia ? Number(mia.train_confidence_mean).toFixed(3) : "—"} />
              <Metric label="Holdout conf." value={mia ? Number(mia.holdout_confidence_mean).toFixed(3) : "—"} />
            </div>
            <Button className="mt-4 w-full" size="sm" disabled={!modelId} onClick={() => runMia.mutate()} loading={runMia.isPending}>
              <Fingerprint className="h-3.5 w-3.5" /> Run MIA
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Flame className="h-4 w-4 text-amber-400" /> Backdoor persistence</CardTitle>
            <Badge tone={backdoor ? (Number(backdoor.persistence_ratio) > 0.5 ? "rose" : "emerald") : "slate"}>
              {backdoor ? (Number(backdoor.persistence_ratio) > 0.5 ? "persists" : "purged") : "not run"}
            </Badge>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed text-slate-400">
              Poison a shard with a trigger, train, then unlearn the poisoned rows and check whether the
              trigger still fires (poisoning-resistant unlearning).
            </p>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <Metric label="Trigger before" value={backdoor ? Number(backdoor.trigger_fires_before_unlearning).toFixed(3) : "—"} />
              <Metric label="Trigger after" value={backdoor ? Number(backdoor.trigger_fires_after_unlearning).toFixed(3) : "—"} />
              <Metric label="Persistence ratio" value={backdoor ? Number(backdoor.persistence_ratio).toFixed(3) : "—"} />
              <Metric label="Poisoned rows" value={backdoor ? String(backdoor.poisoned_records) : "—"} />
            </div>
            <Button className="mt-4 w-full" size="sm" disabled={!modelId} onClick={() => runBackdoor.mutate()} loading={runBackdoor.isPending}>
              <Bug className="h-3.5 w-3.5" /> Run backdoor test
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Eye className="h-4 w-4 text-violet-400" /> Model inversion</CardTitle>
            <Badge tone={inversion ? (Number(inversion.reconstruction_error) > 0.5 ? "amber" : "emerald") : "slate"}>
              {inversion ? "measured" : "not run"}
            </Badge>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed text-slate-400">
              Gradient ascent on the input space reconstructs a prototypical member of the target class.
              Lower reconstruction error = more leakage.
            </p>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <Metric label="Reconstruction error" value={inversion ? Number(inversion.reconstruction_error).toFixed(3) : "—"} />
              <Metric label="Target class" value={inversion ? String(inversion.target_label) : "—"} />
            </div>
            <Button className="mt-4 w-full" size="sm" disabled={!modelId} onClick={() => runInversion.mutate()} loading={runInversion.isPending}>
              <Crosshair className="h-3.5 w-3.5" /> Run inversion
            </Button>
          </CardContent>
        </Card>
      </div>

      {(mia || backdoor || inversion) && (
        <Card>
          <CardHeader>
            <CardTitle>Attack surface summary</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" stroke="#64748b" fontSize={12} />
                <YAxis stroke="#64748b" fontSize={12} domain={[0, 1]} />
                <Tooltip contentStyle={{ background: "#0a0f1c", border: "1px solid #1e293b", borderRadius: 8 }} />
                <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                  {chartData.map((d, i) => <Cell key={i} fill={d.fill} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
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
