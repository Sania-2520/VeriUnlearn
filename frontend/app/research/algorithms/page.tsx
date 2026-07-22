"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import AuthGuard from "../../../components/AuthGuard";
import Navbar from "../../../components/Navbar";
import { api } from "../../../lib/api";

interface Algorithm {
  name: string;
  version: string;
  author: string;
  description: string;
  complexity: string;
  supported_models: string[];
  enabled: boolean;
}

const complexityColor = (c: string) => {
  switch (c) {
    case "low":
      return "bg-green-100 text-green-700";
    case "medium":
      return "bg-yellow-100 text-yellow-700";
    case "high":
      return "bg-red-100 text-red-700";
    default:
      return "bg-gray-100 text-gray-500";
  }
};

export default function AlgorithmsPage() {
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [form, setForm] = useState({
    name: "",
    version: "1.0.0",
    description: "",
    complexity: "medium",
    supported_models: "",
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ["research", "algorithms"],
    queryFn: () => api.research.algorithms(),
  });

  const registerMutation = useMutation({
    mutationFn: () =>
      api.research.registerAlgorithm({
        name: form.name,
        version: form.version,
        description: form.description,
        complexity: form.complexity,
        supported_models: form.supported_models
          .split(",")
          .map((m) => m.trim())
          .filter(Boolean),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["research", "algorithms"] });
      setFormOpen(false);
      setForm({ name: "", version: "1.0.0", description: "", complexity: "medium", supported_models: "" });
    },
  });

  const toggleMutation = useMutation({
    mutationFn: ({ name, enabled }: { name: string; enabled: boolean }) =>
      api.research.toggleAlgorithm(name, enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["research", "algorithms"] });
    },
  });

  const algorithms: Algorithm[] = Array.isArray(data) ? data : data?.algorithms ?? [];

  return (
    <AuthGuard>
      <Navbar />
      <main className="min-h-screen p-8 max-w-7xl mx-auto">
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Algorithm Explorer</h1>
              <p className="text-gray-500 mt-1">Browse and manage registered unlearning algorithms</p>
            </div>
            <button
              onClick={() => setFormOpen(!formOpen)}
              className="bg-primary-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-700"
            >
              {formOpen ? "Cancel" : "Register New Algorithm"}
            </button>
          </div>

          {formOpen && (
            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Register New Algorithm</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                  <input
                    type="text"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    placeholder="e.g. exact-unlearning"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Version</label>
                  <input
                    type="text"
                    value={form.version}
                    onChange={(e) => setForm({ ...form, version: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    placeholder="e.g. 1.0.0"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Complexity</label>
                  <select
                    value={form.complexity}
                    onChange={(e) => setForm({ ...form, complexity: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Supported Models</label>
                  <input
                    type="text"
                    value={form.supported_models}
                    onChange={(e) => setForm({ ...form, supported_models: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    placeholder="Comma-separated, e.g. gpt2, bert-base"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                  <textarea
                    value={form.description}
                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    rows={3}
                    placeholder="Brief description of the algorithm..."
                  />
                </div>
              </div>
              <div className="mt-4 flex justify-end">
                <button
                  onClick={() => registerMutation.mutate()}
                  disabled={!form.name.trim() || registerMutation.isPending}
                  className="bg-primary-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50"
                >
                  {registerMutation.isPending ? "Registering..." : "Register"}
                </button>
              </div>
              {registerMutation.isError && (
                <p className="mt-2 text-sm text-red-600">Failed to register algorithm.</p>
              )}
            </div>
          )}

          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-5">
              <p className="text-sm text-red-700">Failed to load algorithms. Please try again later.</p>
            </div>
          )}

          {isLoading ? (
            <div className="rounded-xl border border-gray-200 bg-white p-8">
              <div className="animate-pulse space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-24 bg-gray-100 rounded-lg" />
                ))}
              </div>
            </div>
          ) : algorithms.length === 0 ? (
            <div className="rounded-xl border border-gray-200 bg-white p-12 text-center">
              <p className="text-gray-500 text-lg font-medium">No algorithms registered</p>
              <p className="text-gray-400 text-sm mt-1">Register an algorithm to get started</p>
            </div>
          ) : (
            <div className="space-y-4">
              {algorithms.map((algo) => (
                <div
                  key={algo.name}
                  className="rounded-xl border border-gray-200 bg-white p-5 hover:shadow-sm transition-shadow"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3">
                        <h3 className="text-lg font-semibold text-gray-900">{algo.name}</h3>
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${complexityColor(algo.complexity)}`}>
                          {algo.complexity}
                        </span>
                        {algo.version && (
                          <span className="text-xs text-gray-400 font-mono">v{algo.version}</span>
                        )}
                      </div>
                      {algo.author && (
                        <p className="text-sm text-gray-500 mt-0.5">by {algo.author}</p>
                      )}
                      {algo.description && (
                        <p className="text-sm text-gray-600 mt-2">{algo.description}</p>
                      )}
                      {algo.supported_models?.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-3">
                          {algo.supported_models.map((model) => (
                            <span
                              key={model}
                              className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full"
                            >
                              {model}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="ml-4 flex-shrink-0">
                      <button
                        onClick={() =>
                          toggleMutation.mutate({ name: algo.name, enabled: !algo.enabled })
                        }
                        disabled={toggleMutation.isPending}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                          algo.enabled ? "bg-primary-600" : "bg-gray-300"
                        }`}
                      >
                        <span
                          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                            algo.enabled ? "translate-x-6" : "translate-x-1"
                          }`}
                        />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </AuthGuard>
  );
}
