"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import AuthGuard from "../../components/AuthGuard";
import Navbar from "../../components/Navbar";

interface Dataset {
  id: number;
  name: string;
  status: string;
  record_count: number;
  dataset_type: string;
}

interface TrainingJob {
  id: number;
  name: string;
  status: string;
  dataset_id: number | null;
  model_version_id: number | null;
  config: Record<string, unknown> | null;
  progress: number;
  current_epoch: number;
  total_epochs: number;
  current_loss: number | null;
  best_loss: number | null;
  error_message: string | null;
  training_time_seconds: number | null;
  created_at: string;
  updated_at: string | null;
}

const authHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem("access_token")}`,
  "Content-Type": "application/json",
});

function formatDuration(seconds: number | null): string {
  if (!seconds) return "-";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export default function TrainingPage() {
  const queryClient = useQueryClient();
  const [showNewJob, setShowNewJob] = useState(false);
  const [jobName, setJobName] = useState("");
  const [selectedDataset, setSelectedDataset] = useState<number | null>(null);
  const [config, setConfig] = useState({
    learning_rate: 0.0002,
    epochs: 3,
    batch_size: 4,
    optimizer: "adamw",
    random_seed: 42,
    lora_r: 16,
    lora_alpha: 32,
  });
  const [filterStatus, setFilterStatus] = useState("");
  const [expandedJob, setExpandedJob] = useState<number | null>(null);

  const { data: datasets = [] } = useQuery<Dataset[]>({
    queryKey: ["datasets"],
    queryFn: async () => {
      const res = await fetch("/api/datasets/?page_size=100&status=ready", { headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` } });
      if (!res.ok) return [];
      const data = await res.json();
      return data.datasets || [];
    },
  });

  const { data: jobsData, isLoading } = useQuery({
    queryKey: ["trainingJobs", filterStatus],
    queryFn: async () => {
      const params = new URLSearchParams({ page_size: "50" });
      if (filterStatus) params.set("status", filterStatus);
      const res = await fetch(`/api/training-jobs/?${params}`, { headers: authHeaders() });
      if (!res.ok) throw new Error("Failed to fetch jobs");
      return res.json();
    },
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      if (!selectedDataset) throw new Error("Select a dataset");
      const res = await fetch("/api/training-jobs/", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          name: jobName || "Training Job",
          dataset_id: selectedDataset,
          config,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed");
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trainingJobs"] });
      setShowNewJob(false);
      setJobName("");
      setSelectedDataset(null);
    },
  });

  const startMutation = useMutation({
    mutationFn: async (jobId: number) => {
      const res = await fetch(`/api/training-jobs/${jobId}/start`, {
        method: "POST",
        headers: authHeaders(),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to start");
      }
      return res.json();
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["trainingJobs"] }),
  });

  const cancelMutation = useMutation({
    mutationFn: async (jobId: number) => {
      const res = await fetch(`/api/training-jobs/${jobId}/cancel`, {
        method: "POST",
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error("Failed to cancel");
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["trainingJobs"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: async (jobId: number) => {
      const res = await fetch(`/api/training-jobs/${jobId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` },
      });
      if (!res.ok) throw new Error("Failed");
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["trainingJobs"] }),
  });

  const jobs = jobsData?.jobs ?? [];

  const statusColor = (s: string) => {
    switch (s) {
      case "completed": return "bg-green-100 text-green-700";
      case "running": return "bg-blue-100 text-blue-700";
      case "failed": return "bg-red-100 text-red-700";
      case "cancelled": return "bg-gray-100 text-gray-500";
      default: return "bg-yellow-100 text-yellow-700";
    }
  };

  return (
    <AuthGuard>
      <Navbar />
      <main className="min-h-screen p-8 max-w-7xl mx-auto">
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Training</h1>
              <p className="text-gray-500 mt-1">Configure and launch model training jobs</p>
            </div>
            <button
              onClick={() => setShowNewJob(true)}
              className="bg-primary-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors"
            >
              New Training Job
            </button>
          </div>

          {showNewJob && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
              <div className="bg-white rounded-xl p-6 w-full max-w-lg max-h-[90vh] overflow-auto space-y-4">
                <h2 className="text-lg font-semibold text-gray-900">New Training Job</h2>

                <input
                  type="text"
                  placeholder="Job name"
                  value={jobName}
                  onChange={(e) => setJobName(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Dataset</label>
                  <select
                    value={selectedDataset || ""}
                    onChange={(e) => setSelectedDataset(Number(e.target.value))}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  >
                    <option value="">Select a dataset</option>
                    {datasets.map((ds) => (
                      <option key={ds.id} value={ds.id}>
                        {ds.name} ({ds.record_count} records, {ds.dataset_type})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Learning Rate</label>
                    <input
                      type="number"
                      step="0.00001"
                      value={config.learning_rate}
                      onChange={(e) => setConfig({ ...config, learning_rate: parseFloat(e.target.value) })}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Epochs</label>
                    <input
                      type="number"
                      value={config.epochs}
                      onChange={(e) => setConfig({ ...config, epochs: parseInt(e.target.value) })}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Batch Size</label>
                    <input
                      type="number"
                      value={config.batch_size}
                      onChange={(e) => setConfig({ ...config, batch_size: parseInt(e.target.value) })}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Optimizer</label>
                    <select
                      value={config.optimizer}
                      onChange={(e) => setConfig({ ...config, optimizer: e.target.value })}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    >
                      <option value="adamw">AdamW</option>
                      <option value="adam">Adam</option>
                      <option value="sgd">SGD</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">LoRA Rank (r)</label>
                    <input
                      type="number"
                      value={config.lora_r}
                      onChange={(e) => setConfig({ ...config, lora_r: parseInt(e.target.value) })}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">LoRA Alpha</label>
                    <input
                      type="number"
                      value={config.lora_alpha}
                      onChange={(e) => setConfig({ ...config, lora_alpha: parseInt(e.target.value) })}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Random Seed</label>
                    <input
                      type="number"
                      value={config.random_seed}
                      onChange={(e) => setConfig({ ...config, random_seed: parseInt(e.target.value) })}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    />
                  </div>
                </div>

                {createMutation.isError && (
                  <p className="text-sm text-red-600 bg-red-50 p-2 rounded-lg">{(createMutation.error as Error).message}</p>
                )}

                <div className="flex gap-3 justify-end pt-2">
                  <button onClick={() => setShowNewJob(false)} className="px-4 py-2 text-sm text-gray-600">Cancel</button>
                  <button
                    onClick={() => createMutation.mutate()}
                    disabled={!selectedDataset || createMutation.isPending}
                    className="px-4 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                  >
                    {createMutation.isPending ? "Creating..." : "Create Job"}
                  </button>
                </div>
              </div>
            </div>
          )}

          <div className="flex gap-2">
            {["", "created", "running", "completed", "failed", "cancelled"].map((s) => (
              <button
                key={s}
                onClick={() => setFilterStatus(s)}
                className={`px-3 py-1.5 text-sm rounded-lg border ${
                  filterStatus === s
                    ? "bg-primary-50 border-primary-300 text-primary-700"
                    : "border-gray-200 text-gray-500 hover:bg-gray-50"
                }`}
              >
                {s || "All"}
              </button>
            ))}
          </div>

          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="rounded-xl border border-gray-200 bg-white p-5 animate-pulse">
                  <div className="h-5 bg-gray-200 rounded w-1/3 mb-3"></div>
                  <div className="h-4 bg-gray-100 rounded w-1/4"></div>
                </div>
              ))}
            </div>
          ) : jobs.length === 0 ? (
            <div className="rounded-xl border border-gray-200 bg-white p-12 text-center">
              <p className="text-gray-500 text-lg font-medium">No training jobs yet</p>
              <p className="text-gray-400 text-sm mt-1">Create a job to start training a model</p>
            </div>
          ) : (
            <div className="space-y-3">
              {jobs.map((job: TrainingJob) => (
                <div key={job.id} className="rounded-xl border border-gray-200 bg-white overflow-hidden">
                  <div
                    className="p-5 cursor-pointer hover:bg-gray-50 transition-colors"
                    onClick={() => setExpandedJob(expandedJob === job.id ? null : job.id)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div>
                          <h3 className="font-medium text-gray-900">{job.name}</h3>
                          <p className="text-sm text-gray-400">Job #{job.id} &middot; {formatDuration(job.training_time_seconds)}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className={`text-xs px-2.5 py-1 rounded-full ${statusColor(job.status)}`}>{job.status}</span>
                        {job.status === "running" && (
                          <div className="w-24">
                            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                              <div className="h-full bg-primary-500 rounded-full transition-all" style={{ width: `${job.progress * 100}%` }} />
                            </div>
                            <p className="text-xs text-gray-400 mt-0.5 text-right">{Math.round(job.progress * 100)}%</p>
                          </div>
                        )}
                        <div className="flex gap-1">
                          {job.status === "created" && (
                            <button onClick={(e) => { e.stopPropagation(); startMutation.mutate(job.id); }} className="text-xs bg-primary-600 text-white px-3 py-1 rounded-md hover:bg-primary-700">Start</button>
                          )}
                          {job.status === "running" && (
                            <button onClick={(e) => { e.stopPropagation(); cancelMutation.mutate(job.id); }} className="text-xs bg-red-50 text-red-600 px-3 py-1 rounded-md hover:bg-red-100">Cancel</button>
                          )}
                          {["completed", "failed", "cancelled"].includes(job.status) && (
                            <button onClick={(e) => { e.stopPropagation(); deleteMutation.mutate(job.id); }} className="text-xs text-red-500 hover:text-red-600 px-2">Delete</button>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  {expandedJob === job.id && (
                    <div className="border-t border-gray-100 p-5 bg-gray-50 space-y-3 text-sm">
                      <div className="grid grid-cols-4 gap-4">
                        <div>
                          <span className="text-gray-400">Dataset ID</span>
                          <p className="text-gray-900">{job.dataset_id ?? "-"}</p>
                        </div>
                        <div>
                          <span className="text-gray-400">Model Version</span>
                          <p className="text-gray-900">{job.model_version_id ? `v${job.model_version_id}` : "-"}</p>
                        </div>
                        <div>
                          <span className="text-gray-400">Current Loss</span>
                          <p className="text-gray-900">{job.current_loss?.toFixed(4) ?? "-"}</p>
                        </div>
                        <div>
                          <span className="text-gray-400">Best Loss</span>
                          <p className="text-gray-900">{job.best_loss?.toFixed(4) ?? "-"}</p>
                        </div>
                      </div>
                      <div className="grid grid-cols-4 gap-4">
                        <div>
                          <span className="text-gray-400">Epoch</span>
                          <p className="text-gray-900">{job.current_epoch}/{job.total_epochs}</p>
                        </div>
                        <div>
                          <span className="text-gray-400">Created</span>
                          <p className="text-gray-900">{new Date(job.created_at).toLocaleString()}</p>
                        </div>
                        {job.config && (
                          <div className="col-span-2">
                            <span className="text-gray-400">Config</span>
                            <pre className="text-xs text-gray-700 bg-white rounded p-2 mt-1 overflow-x-auto">{JSON.stringify(job.config, null, 2)}</pre>
                          </div>
                        )}
                      </div>
                      {job.error_message && (
                        <div className="bg-red-50 text-red-700 text-sm p-3 rounded-lg">{job.error_message}</div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </AuthGuard>
  );
}
