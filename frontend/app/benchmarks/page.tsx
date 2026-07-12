"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import AuthGuard from "../../components/AuthGuard";
import Navbar from "../../components/Navbar";

interface AlgorithmBenchmark {
  name: string;
  recommended: boolean;
  estimated_cost: number;
  estimated_latency: number;
  guarantees: string;
  privacy_score: number;
  utility_retention: number;
  implementation_status: string;
  budget_fit: boolean;
  mia_before: number;
  mia_after: number;
  mia_reduction: number;
}

interface BenchmarkResponse {
  recommended: string;
  dataset_size: number;
  num_deleted: number;
  deletion_ratio: number;
  sensitivity: string;
  latency_budget: number;
  algorithms: AlgorithmBenchmark[];
}

const authHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem("access_token")}`,
  "Content-Type": "application/json",
});

export default function BenchmarksPage() {
  const [datasetSize, setDatasetSize] = useState(1000);
  const [numDeleted, setNumDeleted] = useState(25);
  const [sensitivity, setSensitivity] = useState("medium");
  const [latencyBudget, setLatencyBudget] = useState(300);

  const benchmark = useMutation<BenchmarkResponse>({
    mutationFn: async () => {
      const res = await fetch("/api/unlearning/benchmark", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          dataset_size: datasetSize,
          num_deleted: numDeleted,
          sensitivity,
          latency_budget: latencyBudget,
        }),
      });
      if (!res.ok) throw new Error("Failed to benchmark algorithms");
      return res.json();
    },
  });

  const result = benchmark.data;

  return (
    <AuthGuard>
      <Navbar />
      <main className="min-h-screen p-8 max-w-6xl mx-auto">
        <div className="space-y-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Unlearning Benchmarks</h1>
            <p className="text-gray-500 mt-1">
              Compare privacy, utility, latency, and cost tradeoffs before running deletion.
            </p>
          </div>

          <section className="rounded-xl border border-gray-200 bg-white p-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Dataset Size</label>
                <input
                  type="number"
                  min={1}
                  value={datasetSize}
                  onChange={(e) => setDatasetSize(Number(e.target.value))}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Deleted Samples</label>
                <input
                  type="number"
                  min={1}
                  value={numDeleted}
                  onChange={(e) => setNumDeleted(Number(e.target.value))}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Sensitivity</label>
                <select
                  value={sensitivity}
                  onChange={(e) => setSensitivity(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                >
                  <option value="low">low</option>
                  <option value="medium">medium</option>
                  <option value="high">high</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Latency Budget (s)</label>
                <input
                  type="number"
                  min={1}
                  value={latencyBudget}
                  onChange={(e) => setLatencyBudget(Number(e.target.value))}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
            </div>

            <button
              onClick={() => benchmark.mutate()}
              disabled={benchmark.isPending}
              className="mt-4 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              {benchmark.isPending ? "Running..." : "Compare Algorithms"}
            </button>
          </section>

          {result && (
            <>
              <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="rounded-xl border border-green-200 bg-green-50 p-5">
                  <p className="text-sm text-green-700">Recommended</p>
                  <p className="mt-1 text-2xl font-semibold text-green-900">{result.recommended}</p>
                </div>
                <div className="rounded-xl border border-gray-200 bg-white p-5">
                  <p className="text-sm text-gray-500">Deletion Ratio</p>
                  <p className="mt-1 text-2xl font-semibold text-gray-900">
                    {(result.deletion_ratio * 100).toFixed(2)}%
                  </p>
                </div>
                <div className="rounded-xl border border-gray-200 bg-white p-5">
                  <p className="text-sm text-gray-500">Budget</p>
                  <p className="mt-1 text-2xl font-semibold text-gray-900">{result.latency_budget}s</p>
                </div>
              </section>

              <section className="rounded-xl border border-gray-200 bg-white overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200">
                      <th className="text-left px-4 py-3 font-medium text-gray-500">Algorithm</th>
                      <th className="text-left px-4 py-3 font-medium text-gray-500">Guarantee</th>
                      <th className="text-right px-4 py-3 font-medium text-gray-500">MIA Before</th>
                      <th className="text-right px-4 py-3 font-medium text-gray-500">MIA After</th>
                      <th className="text-right px-4 py-3 font-medium text-gray-500">Latency</th>
                      <th className="text-right px-4 py-3 font-medium text-gray-500">Cost</th>
                      <th className="text-right px-4 py-3 font-medium text-gray-500">Privacy</th>
                      <th className="text-right px-4 py-3 font-medium text-gray-500">Utility</th>
                      <th className="text-left px-4 py-3 font-medium text-gray-500">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.algorithms.map((a) => (
                      <tr key={a.name} className={a.recommended ? "bg-green-50 border-b border-green-100" : "border-b border-gray-100"}>
                        <td className="px-4 py-3 font-medium text-gray-900">
                          {a.name}
                          {a.recommended && <span className="ml-2 text-xs text-green-700">recommended</span>}
                        </td>
                        <td className="px-4 py-3 text-gray-500">{a.guarantees}</td>
                        <td className="px-4 py-3 text-right text-gray-900">{(a.mia_before * 100).toFixed(1)}%</td>
                        <td className="px-4 py-3 text-right text-green-700">{(a.mia_after * 100).toFixed(1)}%</td>
                        <td className="px-4 py-3 text-right text-gray-900">{a.estimated_latency.toFixed(2)}s</td>
                        <td className="px-4 py-3 text-right text-gray-900">{a.estimated_cost.toFixed(2)}</td>
                        <td className="px-4 py-3 text-right text-gray-900">{(a.privacy_score * 100).toFixed(0)}%</td>
                        <td className="px-4 py-3 text-right text-gray-900">{(a.utility_retention * 100).toFixed(0)}%</td>
                        <td className="px-4 py-3">
                          <span className={a.budget_fit ? "text-xs text-green-700" : "text-xs text-yellow-700"}>
                            {a.implementation_status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            </>
          )}
        </div>
      </main>
    </AuthGuard>
  );
}
