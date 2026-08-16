"use client";

import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Database,
  Upload,
  Rocket,
  Trash2,
  Cpu,
  Boxes,
  Activity,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge, statusTone } from "@/components/ui/badge";
import { Table, THead, Th, Td, TRow } from "@/components/ui/table";
import { Spinner } from "@/components/ui/progress";
import { timeAgo } from "@/lib/utils";

interface Dataset {
  id: string;
  name: string;
  description: string | null;
  source_type: string;
  record_count: number;
  feature_names: string[];
  label_column: string | null;
  shard_count: number;
  status: string;
  created_at: string | null;
}

interface MLModel {
  id: string;
  name: string;
  dataset_id: string;
  version: number;
  status: string;
  is_active: boolean;
  weights_hash: string | null;
  metrics: { accuracy?: number; f1?: number; train_records?: number };
  shard_count: number;
}

export default function DatasetsPage() {
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [trainingId, setTrainingId] = useState<string | null>(null);

  const { data: datasets, isLoading } = useQuery<Dataset[]>({
    queryKey: ["datasets"],
    queryFn: () => api.get("/api/v1/datasets?limit=50"),
  });

  const { data: models } = useQuery<MLModel[]>({
    queryKey: ["models"],
    queryFn: () => api.get("/api/v1/models?limit=50"),
  });

  const bootstrap = useMutation({
    mutationFn: () => api.post<Dataset>("/api/v1/datasets/bootstrap/adult?limit=8000&shard_count=4"),
    onSuccess: () => {
      setNotice("Adult Census ingested (8,000 records, 4 shards).");
      qc.invalidateQueries({ queryKey: ["datasets"] });
    },
    onError: (e) => setNotice(e instanceof ApiError ? e.message : "Bootstrap failed"),
  });

  const upload = useMutation({
    mutationFn: (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("shard_count", "4");
      return api.upload<Dataset>("/api/v1/datasets/upload", fd);
    },
    onSuccess: (d) => {
      setNotice(`Ingested ${d.record_count} records from ${d.name}.`);
      qc.invalidateQueries({ queryKey: ["datasets"] });
    },
    onError: (e) => setNotice(e instanceof ApiError ? e.message : "Upload failed"),
  });

  const train = useMutation({
    mutationFn: (datasetId: string) => api.post<MLModel>(`/api/v1/models/train?dataset_id=${datasetId}`),
    onMutate: (datasetId) => setTrainingId(datasetId),
    onSuccess: (m) => {
      setNotice(`SISA model trained — accuracy ${((m.metrics.accuracy ?? 0) * 100).toFixed(1)}% (v${m.version}).`);
      qc.invalidateQueries({ queryKey: ["models"] });
      qc.invalidateQueries({ queryKey: ["datasets"] });
    },
    onSettled: () => setTrainingId(null),
    onError: (e) => setNotice(e instanceof ApiError ? e.message : "Training failed"),
  });

  const remove = useMutation({
    mutationFn: (datasetId: string) => api.delete(`/api/v1/datasets/${datasetId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["datasets"] }),
  });

  const modelFor = (datasetId: string) => models?.find((m) => m.dataset_id === datasetId && m.is_active !== false);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Datasets & Training</h1>
          <p className="mt-1 text-sm text-slate-500">Ingest data, train SISA sharded models, score influence.</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={() => bootstrap.mutate()} loading={bootstrap.isPending}>
            <Database className="h-4 w-4" /> Bootstrap Adult Census
          </Button>
          <Button onClick={() => fileRef.current?.click()} loading={upload.isPending}>
            <Upload className="h-4 w-4" /> Upload CSV
          </Button>
          <input
            ref={fileRef}
            type="file"
            accept=".csv,.json,.jsonl,.txt"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && upload.mutate(e.target.files[0])}
          />
        </div>
      </div>

      {notice && (
        <div className="rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-4 py-3 text-sm text-cyan-200">{notice}</div>
      )}

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner className="h-8 w-8" /></div>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Datasets</CardTitle>
            <Badge tone="cyan">{datasets?.length ?? 0} registered</Badge>
          </CardHeader>
          <Table>
            <THead>
              <tr>
                <Th>Dataset</Th>
                <Th>Records</Th>
                <Th>Shards</Th>
                <Th>Features</Th>
                <Th>Label</Th>
                <Th>Model</Th>
                <Th>Ingested</Th>
                <Th></Th>
              </tr>
            </THead>
            <tbody>
              {(datasets ?? []).map((d) => {
                const m = modelFor(d.id);
                return (
                  <TRow key={d.id}>
                    <Td>
                      <div className="flex items-center gap-2 font-medium text-slate-100">
                        <Database className="h-4 w-4 text-cyan-400" /> {d.name}
                      </div>
                      <div className="text-xs text-slate-500">{d.source_type}</div>
                    </Td>
                    <Td className="mono">{d.record_count}</Td>
                    <Td className="mono">{d.shard_count}</Td>
                    <Td className="max-w-[180px] truncate text-xs text-slate-400">
                      {d.feature_names.slice(0, 4).join(", ")}
                      {d.feature_names.length > 4 ? "…" : ""}
                    </Td>
                    <Td className="mono text-xs">{d.label_column ?? "—"}</Td>
                    <Td>
                      {m ? (
                        <div className="space-y-1">
                          <Badge tone={statusTone(m.status)}>
                            <Cpu className="h-3 w-3" /> v{m.version} · {m.status}
                          </Badge>
                          {m.metrics.accuracy !== undefined && (
                            <div className="text-xs text-slate-500">
                              acc {(m.metrics.accuracy * 100).toFixed(1)}% · f1 {(m.metrics.f1 ?? 0).toFixed(2)}
                            </div>
                          )}
                        </div>
                      ) : (
                        <span className="text-xs text-slate-600">not trained</span>
                      )}
                    </Td>
                    <Td className="text-xs text-slate-500">{timeAgo(d.created_at)}</Td>
                    <Td>
                      <div className="flex gap-2">
                        <Button size="sm" variant="secondary" onClick={() => train.mutate(d.id)} loading={trainingId === d.id}>
                          <Rocket className="h-3.5 w-3.5" /> {m ? "Retrain" : "Train"}
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => remove.mutate(d.id)}>
                          <Trash2 className="h-3.5 w-3.5 text-rose-400" />
                        </Button>
                      </div>
                    </Td>
                  </TRow>
                );
              })}
              {(datasets ?? []).length === 0 && (
                <TRow>
                  <Td colSpan={8} className="py-10 text-center text-slate-500">
                    No datasets yet. Bootstrap the Adult Census benchmark or upload your own CSV.
                  </Td>
                </TRow>
              )}
            </tbody>
          </Table>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        {[
          { icon: Boxes, title: "SISA sharding", desc: "Records are stratified into independent shards; each shard trains its own model. Deleting data retrains only the affected shard." },
          { icon: Activity, title: "Soft-voting aggregation", desc: "Predictions are the mean of shard probabilities — a stable ensemble that degrades gracefully under shard retraining." },
          { icon: Cpu, title: "Influence scoring", desc: "Each record gets an exact Hessian-based influence score on its shard model, used for prioritised deletion and footprint analysis." },
        ].map((f) => (
          <Card key={f.title}>
            <CardContent>
              <f.icon className="mb-3 h-6 w-6 text-violet-400" />
              <h3 className="mb-1 font-semibold text-slate-100">{f.title}</h3>
              <p className="text-sm leading-relaxed text-slate-400">{f.desc}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
