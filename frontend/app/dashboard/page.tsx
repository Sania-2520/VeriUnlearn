"use client";

import { useQuery } from "@tanstack/react-query";
import AuthGuard from "../../components/AuthGuard";
import Navbar from "../../components/Navbar";

interface DashboardStats {
  total_datasets: number;
  total_training_jobs: number;
  total_models: number;
  total_inference_requests: number;
  storage_used_bytes: number;
  training_success_rate: number;
  recent_jobs: { id: number; name: string; status: string; progress: number; created_at: string | null }[];
  recent_models: { id: number; base_model: string; status: string; hash: string; created_at: string | null }[];
  recent_datasets: { id: number; name: string; status: string; record_count: number; created_at: string | null }[];
  activity: { type: string; model: string; latency_ms: number | null; created_at: string | null }[];
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

export default function DashboardPage() {
  const { data: stats, isLoading } = useQuery<DashboardStats>({
    queryKey: ["dashboardStats"],
    queryFn: async () => {
      const res = await fetch("/api/dashboard/stats", {
        headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` },
      });
      if (!res.ok) throw new Error("Failed");
      return res.json();
    },
  });

  const cards = stats
    ? [
        { label: "Datasets", value: stats.total_datasets, icon: "&#128202;", color: "bg-blue-50 text-blue-700", href: "/datasets" },
        { label: "Training Jobs", value: stats.total_training_jobs, icon: "&#9881;", color: "bg-amber-50 text-amber-700", href: "/training" },
        { label: "Models", value: stats.total_models, icon: "&#129504;", color: "bg-purple-50 text-purple-700", href: "/models" },
        { label: "Inferences", value: stats.total_inference_requests, icon: "&#9889;", color: "bg-green-50 text-green-700", href: "/workspace" },
        { label: "Storage", value: formatSize(stats.storage_used_bytes), icon: "&#128190;", color: "bg-gray-50 text-gray-700", href: "" },
        { label: "Success Rate", value: `${stats.training_success_rate}%`, icon: "&#127919;", color: "bg-emerald-50 text-emerald-700", href: "" },
      ]
    : [];

  const statusColor = (s: string) => {
    switch (s) {
      case "completed": case "active": return "bg-green-100 text-green-700";
      case "running": case "ready": return "bg-blue-100 text-blue-700";
      case "failed": return "bg-red-100 text-red-700";
      default: return "bg-gray-100 text-gray-500";
    }
  };

  return (
    <AuthGuard>
      <Navbar />
      <main className="min-h-screen p-8 max-w-7xl mx-auto">
        <div className="space-y-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
            <p className="text-gray-500 mt-1">Overview of your ML platform activity</p>
          </div>

          {isLoading ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div key={i} className="rounded-xl border border-gray-200 bg-white p-5 animate-pulse">
                  <div className="h-8 bg-gray-200 rounded mb-2"></div>
                  <div className="h-4 bg-gray-100 rounded w-2/3"></div>
                </div>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              {cards.map((card) => (
                <a
                  key={card.label}
                  href={card.href || "#"}
                  className={`rounded-xl border border-gray-200 bg-white p-5 hover:shadow-sm transition-shadow ${card.href ? "cursor-pointer" : ""}`}
                >
                  <div className="text-2xl mb-2" dangerouslySetInnerHTML={{ __html: card.icon }} />
                  <div className="text-2xl font-bold text-gray-900">{card.value}</div>
                  <div className="text-sm text-gray-500">{card.label}</div>
                </a>
              ))}
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="rounded-xl border border-gray-200 bg-white">
              <div className="px-5 py-4 border-b border-gray-200">
                <h2 className="font-semibold text-gray-900">Recent Training Jobs</h2>
              </div>
              <div className="p-5">
                {isLoading ? (
                  <div className="animate-pulse space-y-3">
                    {[1, 2, 3].map((i) => <div key={i} className="h-10 bg-gray-100 rounded" />)}
                  </div>
                ) : !stats?.recent_jobs.length ? (
                  <p className="text-gray-400 text-sm">No recent jobs</p>
                ) : (
                  <div className="space-y-2">
                    {stats.recent_jobs.map((job) => (
                      <div key={job.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                        <div>
                          <p className="text-sm font-medium text-gray-900">{job.name}</p>
                          <p className="text-xs text-gray-400">{job.created_at ? new Date(job.created_at).toLocaleDateString() : ""}</p>
                        </div>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(job.status)}`}>{job.status}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white">
              <div className="px-5 py-4 border-b border-gray-200">
                <h2 className="font-semibold text-gray-900">Recent Models</h2>
              </div>
              <div className="p-5">
                {isLoading ? (
                  <div className="animate-pulse space-y-3">
                    {[1, 2, 3].map((i) => <div key={i} className="h-10 bg-gray-100 rounded" />)}
                  </div>
                ) : !stats?.recent_models.length ? (
                  <p className="text-gray-400 text-sm">No models yet</p>
                ) : (
                  <div className="space-y-2">
                    {stats.recent_models.map((m) => (
                      <div key={m.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                        <div>
                          <p className="text-sm font-medium text-gray-900">v{m.id} &middot; {m.base_model.split("/").pop()}</p>
                          <p className="text-xs text-gray-400 font-mono">{m.hash}...</p>
                        </div>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(m.status)}`}>{m.status}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white">
              <div className="px-5 py-4 border-b border-gray-200">
                <h2 className="font-semibold text-gray-900">Recent Datasets</h2>
              </div>
              <div className="p-5">
                {isLoading ? (
                  <div className="animate-pulse space-y-3">
                    {[1, 2, 3].map((i) => <div key={i} className="h-10 bg-gray-100 rounded" />)}
                  </div>
                ) : !stats?.recent_datasets.length ? (
                  <p className="text-gray-400 text-sm">No datasets yet</p>
                ) : (
                  <div className="space-y-2">
                    {stats.recent_datasets.map((d) => (
                      <div key={d.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                        <div>
                          <p className="text-sm font-medium text-gray-900">{d.name}</p>
                          <p className="text-xs text-gray-400">{d.record_count.toLocaleString()} records</p>
                        </div>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(d.status)}`}>{d.status}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white">
              <div className="px-5 py-4 border-b border-gray-200">
                <h2 className="font-semibold text-gray-900">Latest Activity</h2>
              </div>
              <div className="p-5">
                {isLoading ? (
                  <div className="animate-pulse space-y-3">
                    {[1, 2, 3].map((i) => <div key={i} className="h-10 bg-gray-100 rounded" />)}
                  </div>
                ) : !stats?.activity.length ? (
                  <p className="text-gray-400 text-sm">No recent activity</p>
                ) : (
                  <div className="space-y-2">
                    {stats.activity.map((a, i) => (
                      <div key={i} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                        <div>
                          <p className="text-sm text-gray-900">
                            <span className="font-medium">{a.type}</span> &middot; {a.model.split("/").pop()}
                          </p>
                          {a.latency_ms && (
                            <p className="text-xs text-gray-400">{Math.round(a.latency_ms)}ms</p>
                          )}
                        </div>
                        <p className="text-xs text-gray-400">{a.created_at ? new Date(a.created_at).toLocaleDateString() : ""}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </AuthGuard>
  );
}
