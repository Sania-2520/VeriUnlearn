"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import AuthGuard from "../../components/AuthGuard";
import Navbar from "../../components/Navbar";

interface Version {
  id: number;
  base_model: string;
  hash: string;
  status: string;
  num_samples: number;
  train_loss: number | null;
  created_at: string;
}

interface Dataset {
  id: number;
  name: string;
  status: string;
  sample_count: number;
  created_at: string;
}

const authHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem("access_token")}`,
  "Content-Type": "application/json",
});

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const [showCreateDataset, setShowCreateDataset] = useState(false);
  const [datasetName, setDatasetName] = useState("");

  const { data: versionsData, isLoading: versionsLoading } = useQuery<{ versions: Version[] }>({
    queryKey: ["versions"],
    queryFn: async () => {
      const res = await fetch("/api/training/versions", { headers: authHeaders() });
      if (!res.ok) throw new Error("Failed to fetch versions");
      return res.json();
    },
  });

  const { data: datasets = [], isLoading: datasetsLoading } = useQuery<Dataset[]>({
    queryKey: ["datasets"],
    queryFn: async () => {
      const res = await fetch("/api/training/datasets", { headers: authHeaders() });
      if (!res.ok) throw new Error("Failed to fetch datasets");
      return res.json();
    },
  });

  const activateMutation = useMutation({
    mutationFn: async (versionId: number) => {
      const res = await fetch(`/api/training/versions/${versionId}/activate`, {
        method: "POST",
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error("Failed to activate");
      return res.json();
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["versions"] }),
  });

  const createDatasetMutation = useMutation({
    mutationFn: async (name: string) => {
      const res = await fetch("/api/training/datasets", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ name }),
      });
      if (!res.ok) throw new Error("Failed to create dataset");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["datasets"] });
      setShowCreateDataset(false);
      setDatasetName("");
    },
  });

  const buildDatasetMutation = useMutation({
    mutationFn: async (datasetId: number) => {
      const res = await fetch(`/api/training/datasets/${datasetId}/build`, {
        method: "POST",
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error("Failed to build dataset");
      return res.json();
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["datasets"] }),
  });

  const versions = versionsData?.versions ?? [];

  return (
    <AuthGuard>
      <Navbar />
      <main className="min-h-screen p-8 max-w-5xl mx-auto">
        <div className="space-y-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Model Dashboard</h1>
            <p className="text-gray-500 mt-1">Model registry, datasets, and training overview</p>
          </div>

          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold text-gray-900">Datasets</h2>
              <button
                onClick={() => setShowCreateDataset(true)}
                className="text-sm bg-primary-600 text-white px-4 py-1.5 rounded-lg hover:bg-primary-700"
              >
                New Dataset
              </button>
            </div>

            {showCreateDataset && (
              <div className="rounded-xl border border-gray-200 bg-white p-4 mb-4 flex gap-3">
                <input
                  type="text"
                  value={datasetName}
                  onChange={(e) => setDatasetName(e.target.value)}
                  placeholder="Dataset name"
                  className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
                <button
                  onClick={() => createDatasetMutation.mutate(datasetName)}
                  disabled={!datasetName.trim() || createDatasetMutation.isPending}
                  className="rounded-lg bg-primary-600 px-4 py-2 text-sm text-white disabled:opacity-50"
                >
                  Create
                </button>
                <button
                  onClick={() => { setShowCreateDataset(false); setDatasetName(""); }}
                  className="text-sm text-gray-500 px-2"
                >
                  Cancel
                </button>
              </div>
            )}

            {datasetsLoading ? (
              <p className="text-gray-400">Loading...</p>
            ) : datasets.length === 0 ? (
              <div className="rounded-xl border border-gray-200 bg-white p-8 text-center text-gray-400">
                No datasets created yet
              </div>
            ) : (
              <div className="grid gap-3">
                {datasets.map((ds) => (
                  <div
                    key={ds.id}
                    className="rounded-xl border border-gray-200 bg-white p-4 flex items-center justify-between"
                  >
                    <div>
                      <p className="font-medium text-gray-900">{ds.name}</p>
                      <p className="text-sm text-gray-400">
                        {ds.sample_count} samples
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full ${
                          ds.status === "ready"
                            ? "bg-green-100 text-green-700"
                            : "bg-yellow-100 text-yellow-700"
                        }`}
                      >
                        {ds.status}
                      </span>
                      {ds.status !== "ready" && (
                        <button
                          onClick={() => buildDatasetMutation.mutate(ds.id)}
                          disabled={buildDatasetMutation.isPending}
                          className="text-xs text-primary-600 hover:text-primary-700 font-medium"
                        >
                          Build
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 mb-3">Model Versions</h2>
            {versionsLoading ? (
              <p className="text-gray-400">Loading...</p>
            ) : versions.length === 0 ? (
              <div className="rounded-xl border border-gray-200 bg-white p-8 text-center text-gray-400">
                No model versions trained yet
              </div>
            ) : (
              <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200">
                      <th className="text-left px-4 py-3 font-medium text-gray-500">ID</th>
                      <th className="text-left px-4 py-3 font-medium text-gray-500">Model</th>
                      <th className="text-left px-4 py-3 font-medium text-gray-500">Status</th>
                      <th className="text-right px-4 py-3 font-medium text-gray-500">Samples</th>
                      <th className="text-right px-4 py-3 font-medium text-gray-500">Loss</th>
                      <th className="text-center px-4 py-3 font-medium text-gray-500">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {versions.map((v) => (
                      <tr key={v.id} className="border-b border-gray-100">
                        <td className="px-4 py-3 text-gray-900">v{v.id}</td>
                        <td className="px-4 py-3 text-gray-500 truncate max-w-[200px]">
                          {v.base_model}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`text-xs px-2 py-0.5 rounded-full ${
                              v.status === "active"
                                ? "bg-green-100 text-green-700"
                                : v.status === "training"
                                ? "bg-blue-100 text-blue-700"
                                : "bg-gray-100 text-gray-600"
                            }`}
                          >
                            {v.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right text-gray-900">{v.num_samples}</td>
                        <td className="px-4 py-3 text-right text-gray-900">
                          {v.train_loss?.toFixed(4) ?? "-"}
                        </td>
                        <td className="px-4 py-3 text-center">
                          {v.status !== "active" && v.status !== "training" && (
                            <button
                              onClick={() => activateMutation.mutate(v.id)}
                              disabled={activateMutation.isPending}
                              className="text-xs bg-primary-600 text-white px-3 py-1 rounded-md hover:bg-primary-700 disabled:opacity-50"
                            >
                              Activate
                            </button>
                          )}
                          {v.status === "active" && (
                            <span className="text-xs text-green-600 font-medium">In use</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      </main>
    </AuthGuard>
  );
}
