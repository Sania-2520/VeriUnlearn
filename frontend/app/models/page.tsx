"use client";

import React from "react";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import AuthGuard from "../../components/AuthGuard";
import Navbar from "../../components/Navbar";

interface ModelVersion {
  id: number;
  base_model: string;
  hash: string;
  status: string;
  num_samples: number;
  train_loss: number | null;
  eval_loss: number | null;
  metrics: Record<string, unknown> | null;
  created_at: string;
}

const authHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem("access_token")}`,
  "Content-Type": "application/json",
});

export default function ModelsPage() {
  const queryClient = useQueryClient();
  const [filterStatus, setFilterStatus] = useState("");
  const [compareIds, setCompareIds] = useState<[number | null, number | null]>([null, null]);
  const [compareResult, setCompareResult] = useState<Record<string, unknown> | null>(null);
  const [showCompare, setShowCompare] = useState(false);

  const { data: versionsData, isLoading } = useQuery<{ versions: ModelVersion[]; total: number }>({
    queryKey: ["registryVersions", filterStatus],
    queryFn: async () => {
      const params = new URLSearchParams({ page_size: "50" });
      if (filterStatus) params.set("status", filterStatus);
      const res = await fetch(`/api/registry/versions?${params}`, { headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` } });
      if (!res.ok) throw new Error("Failed to fetch models");
      return res.json();
    },
  });

  const activateMutation = useMutation({
    mutationFn: async (id: number) => {
      const res = await fetch(`/api/registry/versions/${id}/activate`, { method: "POST", headers: authHeaders() });
      if (!res.ok) throw new Error("Failed");
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["registryVersions"] }),
  });

  const deployMutation = useMutation({
    mutationFn: async (id: number) => {
      const res = await fetch(`/api/registry/versions/${id}/deploy`, { method: "POST", headers: authHeaders() });
      if (!res.ok) throw new Error("Failed");
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["registryVersions"] }),
  });

  const archiveMutation = useMutation({
    mutationFn: async (id: number) => {
      const res = await fetch(`/api/registry/versions/${id}/archive`, { method: "POST", headers: authHeaders() });
      if (!res.ok) throw new Error("Failed");
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["registryVersions"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      const res = await fetch(`/api/registry/versions/${id}`, { method: "DELETE", headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` } });
      if (!res.ok) throw new Error("Failed");
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["registryVersions"] }),
  });

  const handleCompare = async () => {
    if (!compareIds[0] || !compareIds[1]) return;
    try {
      const res = await fetch(`/api/registry/compare/${compareIds[0]}/${compareIds[1]}`, { headers: authHeaders() });
      if (res.ok) {
        setCompareResult(await res.json());
        setShowCompare(true);
      }
    } catch (e) { console.error("Failed to compare models:", e); }
  };

  const toggleCompare = (id: number) => {
    if (compareIds[0] === id) {
      setCompareIds([null, compareIds[1]]);
    } else if (compareIds[1] === id) {
      setCompareIds([compareIds[0], null]);
    } else if (!compareIds[0]) {
      setCompareIds([id, compareIds[1]]);
    } else if (!compareIds[1]) {
      setCompareIds([compareIds[0], id]);
    }
  };

  const versions = versionsData?.versions ?? [];

  const statusColor = (s: string) => {
    switch (s) {
      case "active": return "bg-green-100 text-green-700";
      case "completed": return "bg-blue-100 text-blue-700";
      case "training": return "bg-yellow-100 text-yellow-700";
      case "archived": return "bg-gray-100 text-gray-500";
      case "failed": return "bg-red-100 text-red-700";
      default: return "bg-gray-100 text-gray-500";
    }
  };

  return (
    <AuthGuard>
      <Navbar />
      <main className="min-h-screen p-8 max-w-7xl mx-auto">
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Model Registry</h1>
              <p className="text-gray-500 mt-1">Manage trained models, compare versions, and deploy</p>
            </div>
            {compareIds[0] && compareIds[1] && (
              <button onClick={handleCompare} className="bg-primary-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-700">
                Compare Selected ({compareIds[0]} vs {compareIds[1]})
              </button>
            )}
            {compareIds[0] && (
              <div className="text-sm text-gray-500">
                Comparing: {compareIds[0]}{compareIds[1] ? ` vs ${compareIds[1]}` : " (select second)"}
                <button onClick={() => setCompareIds([null, null])} className="ml-2 text-red-500">Clear</button>
              </div>
            )}
          </div>

          <div className="flex gap-2">
            {["", "active", "completed", "training", "archived", "failed"].map((s) => (
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
            <div className="rounded-xl border border-gray-200 bg-white p-8 text-center text-gray-400 animate-pulse">Loading...</div>
          ) : versions.length === 0 ? (
            <div className="rounded-xl border border-gray-200 bg-white p-12 text-center">
              <p className="text-gray-500 text-lg font-medium">No models registered yet</p>
              <p className="text-gray-400 text-sm mt-1">Train a model to see it here</p>
            </div>
          ) : (
            <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="text-left px-4 py-3 font-medium text-gray-500 w-8"></th>
                    <th className="text-left px-4 py-3 font-medium text-gray-500">ID</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-500">Base Model</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-500">Status</th>
                    <th className="text-right px-4 py-3 font-medium text-gray-500">Samples</th>
                    <th className="text-right px-4 py-3 font-medium text-gray-500">Train Loss</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-500">Hash</th>
                    <th className="text-center px-4 py-3 font-medium text-gray-500">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {versions.map((v) => {
                    const isSelected = compareIds[0] === v.id || compareIds[1] === v.id;
                    return (
                      <tr key={v.id} className={`border-b border-gray-100 ${isSelected ? "bg-primary-50" : ""}`}>
                        <td className="px-4 py-3">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleCompare(v.id)}
                            className="rounded border-gray-300"
                          />
                        </td>
                        <td className="px-4 py-3 text-gray-900 font-mono">v{v.id}</td>
                        <td className="px-4 py-3 text-gray-500 truncate max-w-[200px]">{v.base_model}</td>
                        <td className="px-4 py-3">
                          <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(v.status)}`}>{v.status}</span>
                        </td>
                        <td className="px-4 py-3 text-right text-gray-900">{v.num_samples}</td>
                        <td className="px-4 py-3 text-right text-gray-900 font-mono">{v.train_loss?.toFixed(4) ?? "-"}</td>
                        <td className="px-4 py-3 text-gray-500 font-mono text-xs">{v.hash.substring(0, 12)}...</td>
                        <td className="px-4 py-3">
                          <div className="flex justify-center gap-1.5">
                            {v.status === "completed" && (
                              <button onClick={() => deployMutation.mutate(v.id)} className="text-xs bg-green-50 text-green-600 px-2 py-1 rounded hover:bg-green-100">Deploy</button>
                            )}
                            {v.status === "training" && (
                              <button onClick={() => activateMutation.mutate(v.id)} className="text-xs bg-primary-50 text-primary-600 px-2 py-1 rounded hover:bg-primary-100">Activate</button>
                            )}
                            {v.status === "active" && (
                              <button onClick={() => archiveMutation.mutate(v.id)} className="text-xs bg-gray-100 text-gray-500 px-2 py-1 rounded hover:bg-gray-200">Archive</button>
                            )}
                            {v.status !== "training" && (
                              <button onClick={() => { if (confirm("Delete this model version?")) deleteMutation.mutate(v.id); }} className="text-xs text-red-500 hover:text-red-600 px-2">Delete</button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {showCompare && compareResult && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
              <div className="bg-white rounded-xl p-6 w-full max-w-lg">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold text-gray-900">Model Comparison</h2>
                  <button onClick={() => setShowCompare(false)} className="text-gray-400 hover:text-gray-600">&times;</button>
                </div>
                {(() => {
                  const v1 = compareResult.version_1 as Record<string, unknown> | undefined;
                  const v2 = compareResult.version_2 as Record<string, unknown> | undefined;
                  const hashMatch = compareResult.hash_match as boolean;
                  if (!v1 || !v2) return null;
                  return (
                    <div className="space-y-4">
                      <div className="grid grid-cols-3 gap-2 text-sm">
                        <div className="font-medium text-gray-500"></div>
                        <div className="font-medium text-gray-700 text-center">v{String(v1.id ?? "")}</div>
                        <div className="font-medium text-gray-700 text-center">v{String(v2.id ?? "")}</div>
                        {["hash", "status", "num_samples", "train_loss"].map((key) => (
                          <React.Fragment key={key}>
                            <div className="text-gray-500 capitalize">{key.replace("_", " ")}</div>
                            <div className="text-gray-900 text-center font-mono text-xs">{String(v1[key] ?? "-")}</div>
                            <div className="text-gray-900 text-center font-mono text-xs">{String(v2[key] ?? "-")}</div>
                          </React.Fragment>
                        ))}
                      </div>
                      {hashMatch ? (
                        <div className="bg-green-50 text-green-700 text-sm p-3 rounded-lg">Models have identical hashes</div>
                      ) : (
                        <div className="bg-yellow-50 text-yellow-700 text-sm p-3 rounded-lg">Models have different hashes</div>
                      )}
                    </div>
                  );
                })()}
              </div>
            </div>
          )}
        </div>
      </main>
    </AuthGuard>
  );
}
