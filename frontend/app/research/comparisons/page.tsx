"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import AuthGuard from "../../../components/AuthGuard";
import Navbar from "../../../components/Navbar";
import { api } from "../../../lib/api";

interface ComparisonItem {
  name: string;
  metrics?: Record<string, unknown>;
  [key: string]: unknown;
}

interface Comparison {
  id: number;
  name: string;
  comparison_type: string;
  items: ComparisonItem[];
  created_at: string | null;
}

const COMPARISON_TYPES = ["algorithm", "model", "dataset", "experiment"] as const;

export default function ComparisonsPage() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState({
    name: "",
    comparison_type: "algorithm",
    items: "",
  });

  const { data: comparisonsData, isLoading: loadingList, error: listError } = useQuery({
    queryKey: ["research", "comparisons"],
    queryFn: () => api.research.comparisons(),
  });

  const comparisonList: Comparison[] = Array.isArray(comparisonsData)
    ? comparisonsData
    : comparisonsData?.comparisons ?? [];

  const selectedComparison = comparisonList.find((c) => c.id === selectedId);

  const createMutation = useMutation({
    mutationFn: () =>
      api.research.createComparison({
        name: createForm.name,
        comparison_type: createForm.comparison_type,
        items: createForm.items
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean)
          .map((name) => ({ name })),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["research", "comparisons"] });
      setCreateOpen(false);
      setCreateForm({ name: "", comparison_type: "algorithm", items: "" });
    },
  });

  const itemKeys: string[] = (() => {
    if (!selectedComparison?.items?.length) return [];
    const keys = new Set<string>();
    for (const item of selectedComparison.items) {
      Object.keys(item).forEach((k) => {
        if (k !== "name") keys.add(k);
      });
      if (item.metrics && typeof item.metrics === "object") {
        Object.keys(item.metrics).forEach((k) => keys.add(`metrics.${k}`));
      }
    }
    return Array.from(keys);
  })();

  function getCellValue(item: ComparisonItem, key: string): string {
    if (key.startsWith("metrics.")) {
      const metricKey = key.slice(7);
      const val = item.metrics?.[metricKey];
      return val != null ? String(val) : "—";
    }
    const val = item[key as keyof ComparisonItem];
    if (val != null && typeof val === "object") {
      return JSON.stringify(val);
    }
    return val != null ? String(val) : "—";
  }

  return (
    <AuthGuard>
      <Navbar />
      <main className="min-h-screen p-8 max-w-7xl mx-auto">
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Comparisons</h1>
              <p className="text-gray-500 mt-1">Compare algorithms, models, datasets, and experiments side by side</p>
            </div>
            <button
              onClick={() => { setCreateOpen(!createOpen); setSelectedId(null); }}
              className="bg-primary-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-700"
            >
              {createOpen ? "Cancel" : "Create Comparison"}
            </button>
          </div>

          {createOpen && (
            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Create Comparison</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                  <input
                    type="text"
                    value={createForm.name}
                    onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    placeholder="e.g. Algorithm Benchmark Q1"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Comparison Type</label>
                  <select
                    value={createForm.comparison_type}
                    onChange={(e) => setCreateForm({ ...createForm, comparison_type: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white"
                  >
                    {COMPARISON_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t.charAt(0).toUpperCase() + t.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Items (comma-separated)</label>
                  <input
                    type="text"
                    value={createForm.items}
                    onChange={(e) => setCreateForm({ ...createForm, items: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    placeholder="e.g. exact-unlearning, sisa-unlearning, gradient-ascent"
                  />
                </div>
              </div>
              <div className="mt-4 flex justify-end">
                <button
                  onClick={() => createMutation.mutate()}
                  disabled={
                    !createForm.name.trim() ||
                    !createForm.items.trim() ||
                    createMutation.isPending
                  }
                  className="bg-primary-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50"
                >
                  {createMutation.isPending ? "Creating..." : "Create"}
                </button>
              </div>
              {createMutation.isError && (
                <p className="mt-2 text-sm text-red-600">Failed to create comparison.</p>
              )}
            </div>
          )}

          {listError && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-5">
              <p className="text-sm text-red-700">Failed to load comparisons. Please try again later.</p>
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
          ) : comparisonList.length === 0 ? (
            <div className="rounded-xl border border-gray-200 bg-white p-12 text-center">
              <p className="text-gray-500 text-lg font-medium">No comparisons yet</p>
              <p className="text-gray-400 text-sm mt-1">Create a comparison to start analyzing items side by side</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {comparisonList.map((comp) => (
                <button
                  key={comp.id}
                  onClick={() => { setSelectedId(comp.id); setCreateOpen(false); }}
                  className={`rounded-xl border p-5 text-left transition-all ${
                    selectedId === comp.id
                      ? "border-primary-300 bg-primary-50 ring-1 ring-primary-200"
                      : "border-gray-200 bg-white hover:shadow-sm"
                  }`}
                >
                  <h3 className="text-base font-semibold text-gray-900">{comp.name}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 font-medium">
                      {comp.comparison_type}
                    </span>
                    <span className="text-xs text-gray-400">
                      {comp.items?.length ?? 0} item{(comp.items?.length ?? 0) !== 1 ? "s" : ""}
                    </span>
                  </div>
                  {comp.created_at && (
                    <p className="text-xs text-gray-400 mt-2">{new Date(comp.created_at).toLocaleDateString()}</p>
                  )}
                </button>
              ))}
            </div>
          )}

          {selectedComparison && (
            <div className="rounded-xl border border-gray-200 bg-white">
              <div className="px-5 py-4 border-b border-gray-200">
                <h2 className="font-semibold text-gray-900">{selectedComparison.name}</h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  Type: {selectedComparison.comparison_type} &middot;{" "}
                  {selectedComparison.items?.length ?? 0} items
                </p>
              </div>
              <div className="p-5">
                {selectedComparison.items?.length ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-gray-500 border-b border-gray-100">
                          <th className="pb-2 font-medium">Item Name</th>
                          {itemKeys.map((key) => (
                            <th key={key} className="pb-2 font-medium text-right">
                              {key}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {selectedComparison.items.map((item, idx) => (
                          <tr
                            key={idx}
                            className="border-b border-gray-50 last:border-0"
                          >
                            <td className="py-2.5 font-medium text-gray-900">{item.name}</td>
                            {itemKeys.map((key) => (
                              <td key={key} className="py-2.5 text-right font-mono text-gray-700">
                                {getCellValue(item, key)}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-gray-400 text-sm text-center py-6">No items in this comparison.</p>
                )}
              </div>
            </div>
          )}
        </div>
      </main>
    </AuthGuard>
  );
}
