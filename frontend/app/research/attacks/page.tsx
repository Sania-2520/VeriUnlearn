"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import AuthGuard from "../../../components/AuthGuard";
import Navbar from "../../../components/Navbar";
import { api } from "../../../lib/api";

interface AttackType {
  name: string;
  description: string;
  risk_baseline: string;
}

interface AttackResult {
  id: number;
  attack_type: string;
  phase: string;
  success_rate: number;
  confidence: number;
  leakage_score: number;
  risk_level: string;
  created_at: string | null;
}

function riskBadge(level: string) {
  const l = level?.toLowerCase() ?? "";
  if (l === "high") return <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-medium">High</span>;
  if (l === "medium") return <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700 font-medium">Medium</span>;
  if (l === "low") return <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700 font-medium">Low</span>;
  return <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 font-medium">{level || "—"}</span>;
}

export default function AttacksPage() {
  const queryClient = useQueryClient();
  const [selectedType, setSelectedType] = useState<string | null>(null);

  const { data: typesData, isLoading: loadingTypes, error: typesError } = useQuery({
    queryKey: ["research", "attackTypes"],
    queryFn: () => api.research.attackTypes(),
  });

  const { data: resultsData, isLoading: loadingResults } = useQuery({
    queryKey: ["research", "attackResults"],
    queryFn: () => api.research.attackResults(),
  });

  const runAttackMutation = useMutation({
    mutationFn: (attackType: string) => api.research.runAttack({ attack_type: attackType }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["research", "attackResults"] });
      setSelectedType(null);
    },
  });

  const types: AttackType[] = Array.isArray(typesData)
    ? typesData
    : typesData?.types ?? [];

  const results: AttackResult[] = Array.isArray(resultsData)
    ? resultsData
    : resultsData?.results ?? [];

  const totalAttacks = results.length;
  const beforeResults = results.filter((r) => r.phase?.toLowerCase() === "before");
  const afterResults = results.filter((r) => r.phase?.toLowerCase() === "after");
  const avgBefore = beforeResults.length
    ? beforeResults.reduce((s, r) => s + (r.success_rate ?? 0), 0) / beforeResults.length
    : 0;
  const avgAfter = afterResults.length
    ? afterResults.reduce((s, r) => s + (r.success_rate ?? 0), 0) / afterResults.length
    : 0;
  const improvement = avgBefore > 0 ? ((avgBefore - avgAfter) / avgBefore) * 100 : 0;

  return (
    <AuthGuard>
      <Navbar />
      <main className="min-h-screen p-8 max-w-7xl mx-auto">
        <div className="space-y-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Privacy Attacks</h1>
            <p className="text-gray-500 mt-1">Evaluate model privacy through membership inference, model inversion, and other attacks</p>
          </div>

          {/* Summary Stats */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="rounded-xl border border-gray-200 bg-white p-5">
              <div className="text-sm text-gray-500">Total Attacks</div>
              <div className="text-2xl font-bold text-gray-900 mt-1">{totalAttacks}</div>
            </div>
            <div className="rounded-xl border border-gray-200 bg-white p-5">
              <div className="text-sm text-gray-500">Avg Success (Before)</div>
              <div className="text-2xl font-bold text-red-600 mt-1">{(avgBefore * 100).toFixed(1)}%</div>
            </div>
            <div className="rounded-xl border border-gray-200 bg-white p-5">
              <div className="text-sm text-gray-500">Avg Success (After)</div>
              <div className="text-2xl font-bold text-green-600 mt-1">{(avgAfter * 100).toFixed(1)}%</div>
            </div>
            <div className="rounded-xl border border-gray-200 bg-white p-5">
              <div className="text-sm text-gray-500">Overall Improvement</div>
              <div className="text-2xl font-bold text-primary-600 mt-1">{improvement > 0 ? `-${improvement.toFixed(1)}%` : "—"}</div>
            </div>
          </div>

          {typesError && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-5">
              <p className="text-sm text-red-700">Failed to load attack types. Please try again later.</p>
            </div>
          )}

          {/* Attack Types */}
          <div>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Available Attacks</h2>
            {loadingTypes ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="rounded-xl border border-gray-200 bg-white p-5 animate-pulse">
                    <div className="h-5 bg-gray-200 rounded w-1/2 mb-3" />
                    <div className="h-4 bg-gray-100 rounded mb-2" />
                    <div className="h-4 bg-gray-100 rounded w-3/4" />
                  </div>
                ))}
              </div>
            ) : types.length === 0 ? (
              <div className="rounded-xl border border-gray-200 bg-white p-12 text-center">
                <p className="text-gray-500 text-lg font-medium">No attack types available</p>
                <p className="text-gray-400 text-sm mt-1">Check back later for available privacy attacks</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {types.map((t) => (
                  <div key={t.name} className="rounded-xl border border-gray-200 bg-white p-5 hover:shadow-sm transition-shadow">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="text-base font-semibold text-gray-900">{t.name}</h3>
                        <p className="text-sm text-gray-500 mt-1">{t.description || "No description"}</p>
                        <div className="mt-3">{riskBadge(t.risk_baseline)}</div>
                      </div>
                    </div>
                    <button
                      onClick={() => runAttackMutation.mutate(t.name)}
                      disabled={runAttackMutation.isPending}
                      className="mt-4 w-full bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50 transition-colors"
                    >
                      {runAttackMutation.isPending && selectedType === t.name ? "Running..." : "Run Attack"}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Results Table */}
          <div className="rounded-xl border border-gray-200 bg-white">
            <div className="px-5 py-4 border-b border-gray-200">
              <h2 className="font-semibold text-gray-900">Attack Results</h2>
            </div>
            <div className="p-5">
              {loadingResults ? (
                <div className="animate-pulse space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-10 bg-gray-100 rounded" />
                  ))}
                </div>
              ) : results.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-gray-400 text-sm">No attack results yet</p>
                  <p className="text-gray-300 text-xs mt-1">Run an attack above to see results here</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-gray-500 border-b border-gray-100">
                        <th className="pb-2 font-medium">Attack Type</th>
                        <th className="pb-2 font-medium">Phase</th>
                        <th className="pb-2 font-medium text-right">Success Rate</th>
                        <th className="pb-2 font-medium text-right">Confidence</th>
                        <th className="pb-2 font-medium text-right">Leakage Score</th>
                        <th className="pb-2 font-medium">Risk Level</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.map((r) => (
                        <tr key={r.id} className="border-b border-gray-50 last:border-0">
                          <td className="py-2.5 font-medium text-gray-900">{r.attack_type}</td>
                          <td className="py-2.5">
                            <span className={`text-xs px-2 py-0.5 rounded-full ${
                              r.phase?.toLowerCase() === "before"
                                ? "bg-red-100 text-red-700"
                                : "bg-green-100 text-green-700"
                            }`}>
                              {r.phase || "—"}
                            </span>
                          </td>
                          <td className="py-2.5 text-right font-mono text-gray-900">
                            {r.success_rate != null ? `${(r.success_rate * 100).toFixed(1)}%` : "—"}
                          </td>
                          <td className="py-2.5 text-right font-mono text-gray-900">
                            {r.confidence != null ? `${(r.confidence * 100).toFixed(1)}%` : "—"}
                          </td>
                          <td className="py-2.5 text-right font-mono text-gray-900">
                            {r.leakage_score != null ? r.leakage_score.toFixed(3) : "—"}
                          </td>
                          <td className="py-2.5">{riskBadge(r.risk_level)}</td>
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
