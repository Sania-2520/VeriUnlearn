"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import AuthGuard from "../../../components/AuthGuard";
import Navbar from "../../../components/Navbar";
import { api } from "../../../lib/api";

interface Leaderboard {
  id: number;
  name: string;
  ranking_metric: string | null;
  created_at: string | null;
}

interface LeaderboardEntry {
  id: number;
  algorithm_name: string;
  score: number;
  scores_json: Record<string, number> | null;
  created_at: string | null;
}

const MEDALS = ["🥇", "🥈", "🥉"];

export default function LeaderboardsPage() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState({ name: "", ranking_metric: "" });
  const [entryFormOpen, setEntryFormOpen] = useState(false);
  const [entryForm, setEntryForm] = useState({ algorithm_name: "", score: "" });

  const { data: leaderboards, isLoading: loadingList, error: listError } = useQuery({
    queryKey: ["research", "leaderboards"],
    queryFn: () => api.research.leaderboards(),
  });

  const { data: entriesData, isLoading: loadingEntries } = useQuery({
    queryKey: ["research", "leaderboardEntries", selectedId],
    queryFn: () => api.research.leaderboardEntries(selectedId!),
    enabled: selectedId !== null,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      api.research.createLeaderboard({
        name: createForm.name,
        ranking_metric: createForm.ranking_metric || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["research", "leaderboards"] });
      setCreateOpen(false);
      setCreateForm({ name: "", ranking_metric: "" });
    },
  });

  const addEntryMutation = useMutation({
    mutationFn: () =>
      api.research.addLeaderboardEntry(selectedId!, {
        algorithm_name: entryForm.algorithm_name,
        score: parseFloat(entryForm.score),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["research", "leaderboardEntries", selectedId] });
      queryClient.invalidateQueries({ queryKey: ["research", "leaderboards"] });
      setEntryFormOpen(false);
      setEntryForm({ algorithm_name: "", score: "" });
    },
  });

  const lbList: Leaderboard[] = Array.isArray(leaderboards) ? leaderboards : leaderboards?.leaderboards ?? [];
  const rawEntries: LeaderboardEntry[] = Array.isArray(entriesData)
    ? entriesData
    : entriesData?.entries ?? [];
  const entries = [...rawEntries].sort((a, b) => b.score - a.score);

  const selectedLb = lbList.find((lb) => lb.id === selectedId);

  return (
    <AuthGuard>
      <Navbar />
      <main className="min-h-screen p-8 max-w-7xl mx-auto">
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Leaderboards</h1>
              <p className="text-gray-500 mt-1">Rank algorithms by performance across benchmarks</p>
            </div>
            <button
              onClick={() => { setCreateOpen(!createOpen); setSelectedId(null); }}
              className="bg-primary-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-700"
            >
              {createOpen ? "Cancel" : "Create Leaderboard"}
            </button>
          </div>

          {createOpen && (
            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Create Leaderboard</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                  <input
                    type="text"
                    value={createForm.name}
                    onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    placeholder="e.g. Unlearning Accuracy Rankings"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Ranking Metric</label>
                  <input
                    type="text"
                    value={createForm.ranking_metric}
                    onChange={(e) => setCreateForm({ ...createForm, ranking_metric: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    placeholder="e.g. accuracy, f1_score"
                  />
                </div>
              </div>
              <div className="mt-4 flex justify-end">
                <button
                  onClick={() => createMutation.mutate()}
                  disabled={!createForm.name.trim() || createMutation.isPending}
                  className="bg-primary-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50"
                >
                  {createMutation.isPending ? "Creating..." : "Create"}
                </button>
              </div>
              {createMutation.isError && (
                <p className="mt-2 text-sm text-red-600">Failed to create leaderboard.</p>
              )}
            </div>
          )}

          {listError && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-5">
              <p className="text-sm text-red-700">Failed to load leaderboards. Please try again later.</p>
            </div>
          )}

          {loadingList ? (
            <div className="rounded-xl border border-gray-200 bg-white p-8">
              <div className="animate-pulse space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-16 bg-gray-100 rounded-lg" />
                ))}
              </div>
            </div>
          ) : lbList.length === 0 ? (
            <div className="rounded-xl border border-gray-200 bg-white p-12 text-center">
              <p className="text-gray-500 text-lg font-medium">No leaderboards yet</p>
              <p className="text-gray-400 text-sm mt-1">Create a leaderboard to start ranking algorithms</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {lbList.map((lb) => (
                <button
                  key={lb.id}
                  onClick={() => { setSelectedId(lb.id); setCreateOpen(false); }}
                  className={`rounded-xl border p-5 text-left transition-all ${
                    selectedId === lb.id
                      ? "border-primary-300 bg-primary-50 ring-1 ring-primary-200"
                      : "border-gray-200 bg-white hover:shadow-sm"
                  }`}
                >
                  <h3 className="text-base font-semibold text-gray-900">{lb.name}</h3>
                  {lb.ranking_metric && (
                    <p className="text-xs text-gray-500 mt-1">Metric: {lb.ranking_metric}</p>
                  )}
                  {lb.created_at && (
                    <p className="text-xs text-gray-400 mt-1">{new Date(lb.created_at).toLocaleDateString()}</p>
                  )}
                </button>
              ))}
            </div>
          )}

          {selectedId !== null && (
            <div className="rounded-xl border border-gray-200 bg-white">
              <div className="px-5 py-4 border-b border-gray-200 flex items-center justify-between">
                <div>
                  <h2 className="font-semibold text-gray-900">
                    {selectedLb?.name ?? "Leaderboard"} — Rankings
                  </h2>
                  {selectedLb?.ranking_metric && (
                    <p className="text-xs text-gray-500 mt-0.5">Ranked by {selectedLb.ranking_metric}</p>
                  )}
                </div>
                <button
                  onClick={() => { setEntryFormOpen(!entryFormOpen); }}
                  className="bg-primary-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-primary-700"
                >
                  {entryFormOpen ? "Cancel" : "Add Entry"}
                </button>
              </div>

              {entryFormOpen && (
                <div className="px-5 py-4 border-b border-gray-100 bg-gray-50">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Algorithm Name</label>
                      <input
                        type="text"
                        value={entryForm.algorithm_name}
                        onChange={(e) => setEntryForm({ ...entryForm, algorithm_name: e.target.value })}
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                        placeholder="e.g. exact-unlearning"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Score</label>
                      <input
                        type="number"
                        step="any"
                        value={entryForm.score}
                        onChange={(e) => setEntryForm({ ...entryForm, score: e.target.value })}
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                        placeholder="e.g. 0.95"
                      />
                    </div>
                    <button
                      onClick={() => addEntryMutation.mutate()}
                      disabled={!entryForm.algorithm_name.trim() || !entryForm.score.trim() || addEntryMutation.isPending}
                      className="bg-primary-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50"
                    >
                      {addEntryMutation.isPending ? "Adding..." : "Add"}
                    </button>
                  </div>
                  {addEntryMutation.isError && (
                    <p className="mt-2 text-sm text-red-600">Failed to add entry.</p>
                  )}
                </div>
              )}

              <div className="p-5">
                {loadingEntries ? (
                  <div className="animate-pulse space-y-3">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="h-12 bg-gray-100 rounded" />
                    ))}
                  </div>
                ) : entries.length === 0 ? (
                  <p className="text-gray-400 text-sm text-center py-6">No entries yet. Add an algorithm to get started.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-gray-500 border-b border-gray-100">
                          <th className="pb-2 font-medium w-16">Rank</th>
                          <th className="pb-2 font-medium">Algorithm</th>
                          <th className="pb-2 font-medium text-right">Score</th>
                          <th className="pb-2 font-medium">Breakdown</th>
                        </tr>
                      </thead>
                      <tbody>
                        {entries.map((entry, idx) => {
                          const scoresBreakdown =
                            entry.scores_json && typeof entry.scores_json === "object"
                              ? Object.entries(entry.scores_json)
                              : null;
                          return (
                            <tr
                              key={entry.id}
                              className={`border-b border-gray-50 last:border-0 ${idx < 3 ? "bg-gray-50/50" : ""}`}
                            >
                              <td className="py-2.5 font-medium text-gray-900">
                                <span className="inline-flex items-center gap-1.5">
                                  {idx < 3 && (
                                    <span className="text-lg">{MEDALS[idx]}</span>
                                  )}
                                  <span className={idx >= 3 ? "text-gray-500" : ""}>{idx + 1}</span>
                                </span>
                              </td>
                              <td className="py-2.5 font-medium text-gray-900">{entry.algorithm_name}</td>
                              <td className="py-2.5 text-right font-mono font-semibold text-gray-900">
                                {entry.score}
                              </td>
                              <td className="py-2.5">
                                {scoresBreakdown && scoresBreakdown.length > 0 ? (
                                  <div className="flex flex-wrap gap-1.5">
                                    {scoresBreakdown.map(([key, val]) => (
                                      <span
                                        key={key}
                                        className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full"
                                      >
                                        {key}: {val}
                                      </span>
                                    ))}
                                  </div>
                                ) : (
                                  <span className="text-gray-400 text-xs">—</span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </main>
    </AuthGuard>
  );
}
