"use client";

import { useQuery } from "@tanstack/react-query";
import AuthGuard from "../../components/AuthGuard";
import Navbar from "../../components/Navbar";
import { api } from "../../lib/api";

const QUICK_LINKS = [
  { label: "Algorithms", href: "/research/algorithms", icon: "&#128295;", color: "bg-blue-50 text-blue-700" },
  { label: "Leaderboards", href: "/research/leaderboards", icon: "&#127942;", color: "bg-amber-50 text-amber-700" },
  { label: "Attacks", href: "/research/attacks", icon: "&#128737;", color: "bg-red-50 text-red-700" },
  { label: "Comparisons", href: "/research/comparisons", icon: "&#128200;", color: "bg-purple-50 text-purple-700" },
  { label: "Reports", href: "/research/reports", icon: "&#128196;", color: "bg-green-50 text-green-700" },
];

interface Algorithm { id: number; name: string; enabled: boolean; }
interface Benchmark { id: number; name: string; status: string; created_at: string | null; }
interface Leaderboard { id: number; name: string; }
interface AttackResult { id: number; attack_type: string; phase: string; }
interface AttackResponse { results: AttackResult[]; summary: Record<string, unknown>; }

export default function ResearchDashboardPage() {
  const { data: algorithms, isLoading: loadingAlgo } = useQuery({
    queryKey: ["research", "algorithms"],
    queryFn: () => api.research.algorithms(),
  });

  const { data: benchmarks, isLoading: loadingBench } = useQuery({
    queryKey: ["research", "benchmarks"],
    queryFn: () => api.research.benchmarks(),
  });

  const { data: leaderboards, isLoading: loadingLB } = useQuery({
    queryKey: ["research", "leaderboards"],
    queryFn: () => api.research.leaderboards(),
  });

  const { data: attackResults, isLoading: loadingAttacks } = useQuery({
    queryKey: ["research", "attackResults"],
    queryFn: () => api.research.attackResults(),
  });

  const attackData = attackResults as AttackResponse | undefined;
  const attackList: AttackResult[] = attackData?.results || [];

  const isLoading = loadingAlgo || loadingBench || loadingLB || loadingAttacks;
  const hasError = !isLoading && (!algorithms || !benchmarks || !leaderboards || !attackResults);

  const algoList: Algorithm[] = Array.isArray(algorithms) ? algorithms : [];
  const benchList: Benchmark[] = Array.isArray(benchmarks) ? benchmarks : [];
  const lbList: Leaderboard[] = Array.isArray(leaderboards) ? leaderboards : [];

  const statCards = [
    { label: "Total Algorithms", value: algoList.length, icon: "&#128295;", color: "bg-blue-50 text-blue-700" },
    { label: "Active Benchmarks", value: benchList.length, icon: "&#9881;", color: "bg-amber-50 text-amber-700" },
    { label: "Leaderboard Rankings", value: lbList.length, icon: "&#127942;", color: "bg-purple-50 text-purple-700" },
    { label: "Attack Results", value: attackList.length, icon: "&#128737;", color: "bg-red-50 text-red-700" },
  ];

  const statusColor = (s: string) => {
    switch (s) {
      case "completed": case "active": case "success": return "bg-green-100 text-green-700";
      case "running": case "pending": return "bg-blue-100 text-blue-700";
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
            <h1 className="text-3xl font-bold text-gray-900">Research Dashboard</h1>
            <p className="text-gray-500 mt-1">Overview of research algorithms, benchmarks, and attack analysis</p>
          </div>

          {hasError && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-5">
              <p className="text-sm text-red-700">Failed to load research data. Please try again later.</p>
            </div>
          )}

          {isLoading ? (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="rounded-xl border border-gray-200 bg-white p-5 animate-pulse">
                  <div className="h-8 bg-gray-200 rounded mb-2"></div>
                  <div className="h-4 bg-gray-100 rounded w-2/3"></div>
                </div>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {statCards.map((card) => (
                <div
                  key={card.label}
                  className="rounded-xl border border-gray-200 bg-white p-5 hover:shadow-sm transition-shadow"
                >
                  <div className="text-2xl mb-2" dangerouslySetInnerHTML={{ __html: card.icon }} />
                  <div className="text-2xl font-bold text-gray-900">{card.value}</div>
                  <div className="text-sm text-gray-500">{card.label}</div>
                </div>
              ))}
            </div>
          )}

          <div>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Links</h2>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {QUICK_LINKS.map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  className={`rounded-xl border border-gray-200 bg-white p-4 hover:shadow-sm transition-shadow cursor-pointer`}
                >
                  <div className="text-xl mb-2" dangerouslySetInnerHTML={{ __html: link.icon }} />
                  <div className="text-sm font-medium text-gray-900">{link.label}</div>
                </a>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white">
            <div className="px-5 py-4 border-b border-gray-200">
              <h2 className="font-semibold text-gray-900">Recent Benchmark Runs</h2>
            </div>
            <div className="p-5">
              {isLoading ? (
                <div className="animate-pulse space-y-3">
                  {[1, 2, 3].map((i) => <div key={i} className="h-10 bg-gray-100 rounded" />)}
                </div>
              ) : !benchList.length ? (
                <p className="text-gray-400 text-sm">No benchmark runs yet</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-gray-500 border-b border-gray-100">
                        <th className="pb-2 font-medium">Name</th>
                        <th className="pb-2 font-medium">Status</th>
                        <th className="pb-2 font-medium">Created</th>
                      </tr>
                    </thead>
                    <tbody>
                      {benchList.slice(0, 10).map((b) => (
                        <tr key={b.id} className="border-b border-gray-50 last:border-0">
                          <td className="py-2.5 font-medium text-gray-900">{b.name}</td>
                          <td className="py-2.5">
                            <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(b.status)}`}>
                              {b.status}
                            </span>
                          </td>
                          <td className="py-2.5 text-gray-400">
                            {b.created_at ? new Date(b.created_at).toLocaleDateString() : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white">
            <div className="px-5 py-4 border-b border-gray-200">
              <h2 className="font-semibold text-gray-900">Recent Attack Results</h2>
            </div>
            <div className="p-5">
              {isLoading ? (
                <div className="animate-pulse space-y-3">
                  {[1, 2, 3].map((i) => <div key={i} className="h-10 bg-gray-100 rounded" />)}
                </div>
              ) : !attackList.length ? (
                <p className="text-gray-400 text-sm">No attack results yet</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-gray-500 border-b border-gray-100">
                        <th className="pb-2 font-medium">Attack Type</th>
                        <th className="pb-2 font-medium">Phase</th>
                        <th className="pb-2 font-medium">ID</th>
                      </tr>
                    </thead>
                    <tbody>
                      {attackList.slice(0, 10).map((a) => (
                        <tr key={a.id} className="border-b border-gray-50 last:border-0">
                          <td className="py-2.5 font-medium text-gray-900">{a.attack_type}</td>
                          <td className="py-2.5">
                            <span className={`text-xs px-2 py-0.5 rounded-full ${a.phase === "before" ? "bg-yellow-100 text-yellow-700" : "bg-green-100 text-green-700"}`}>
                              {a.phase}
                            </span>
                          </td>
                          <td className="py-2.5 text-gray-400 font-mono text-xs">#{a.id}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </AuthGuard>
  );
}
