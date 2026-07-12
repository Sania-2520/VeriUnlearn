"use client";

import { useEffect, useState } from "react";
import AuthGuard from "../../components/AuthGuard";
import Navbar from "../../components/Navbar";

const authHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem("access_token")}`,
  "Content-Type": "application/json",
});

interface LineageEntry {
  id: number;
  base_model: string;
  status: string;
  hash: string;
  parent_version_id: number | null;
  created_at: string;
}

interface VersionStats {
  total: number;
  active: number;
  completed: number;
  training: number;
  failed: number;
}

export default function LineagePage() {
  const [versions, setVersions] = useState<any[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [lineage, setLineage] = useState<LineageEntry[]>([]);
  const [stats, setStats] = useState<VersionStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchVersions();
    fetchStats();
  }, []);

  const fetchVersions = async () => {
    try {
      const res = await fetch("/api/v1/training/versions", { headers: authHeaders() });
      if (res.ok) {
        const data = await res.json();
        setVersions(data.versions || []);
      }
    } catch {}
    setLoading(false);
  };

  const fetchStats = async () => {
    try {
      const res = await fetch("/api/v1/registry/stats", { headers: authHeaders() });
      if (res.ok) setStats(await res.json());
    } catch {}
  };

  const fetchLineage = async (versionId: number) => {
    setSelectedVersion(versionId);
    try {
      const res = await fetch(`/api/v1/registry/versions/${versionId}/lineage`, { headers: authHeaders() });
      if (res.ok) {
        const data = await res.json();
        setLineage(data.lineage || []);
      }
    } catch {}
  };

  return (
    <AuthGuard>
      <Navbar />
      <main className="min-h-screen p-8 max-w-6xl mx-auto">
        <div className="space-y-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Model Lineage</h1>
            <p className="text-gray-500 mt-1">Track model version history and ancestry</p>
          </div>

          {stats && (
            <div className="grid grid-cols-5 gap-4">
              {[
                { label: "Total", value: stats.total, color: "bg-gray-100" },
                { label: "Active", value: stats.active, color: "bg-green-100" },
                { label: "Completed", value: stats.completed, color: "bg-blue-100" },
                { label: "Training", value: stats.training, color: "bg-yellow-100" },
                { label: "Failed", value: stats.failed, color: "bg-red-100" },
              ].map((s) => (
                <div key={s.label} className={`${s.color} rounded-xl p-4 text-center`}>
                  <p className="text-2xl font-bold text-gray-900">{s.value}</p>
                  <p className="text-sm text-gray-600">{s.label}</p>
                </div>
              ))}
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">All Versions</h2>
              {loading ? (
                <p className="text-gray-400">Loading...</p>
              ) : versions.length === 0 ? (
                <p className="text-gray-400 text-center py-8">No versions yet</p>
              ) : (
                <div className="space-y-2 max-h-[500px] overflow-y-auto">
                  {versions.map((v) => (
                    <button
                      key={v.id}
                      onClick={() => fetchLineage(v.id)}
                      className={`w-full text-left p-3 rounded-lg border transition ${
                        selectedVersion === v.id
                          ? "border-primary-500 bg-primary-50"
                          : "border-gray-200 hover:bg-gray-50"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium text-gray-900">v{v.id}</p>
                          <p className="text-xs text-gray-500">{v.base_model}</p>
                        </div>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          v.status === "active" ? "bg-green-100 text-green-700" :
                          v.status === "completed" ? "bg-blue-100 text-blue-700" :
                          v.status === "training" ? "bg-yellow-100 text-yellow-700" :
                          "bg-gray-100 text-gray-700"
                        }`}>
                          {v.status}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Lineage Trail</h2>
              {lineage.length === 0 ? (
                <p className="text-gray-400 text-center py-8">Select a version to view lineage</p>
              ) : (
                <div className="space-y-3">
                  {lineage.map((entry, idx) => (
                    <div key={entry.id} className="flex items-start gap-3">
                      <div className="flex flex-col items-center">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                          idx === lineage.length - 1 ? "bg-primary-600 text-white" : "bg-gray-200 text-gray-600"
                        }`}>
                          {idx + 1}
                        </div>
                        {idx < lineage.length - 1 && (
                          <div className="w-0.5 h-8 bg-gray-300 mt-1" />
                        )}
                      </div>
                      <div className="flex-1 pb-4">
                        <p className="font-medium text-gray-900">Version {entry.id}</p>
                        <p className="text-xs text-gray-500">{entry.base_model}</p>
                        <p className="text-xs text-gray-400 font-mono mt-1">
                          {entry.hash?.slice(0, 16)}...
                        </p>
                        <p className="text-xs text-gray-400">
                          {entry.created_at ? new Date(entry.created_at).toLocaleString() : ""}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </AuthGuard>
  );
}
