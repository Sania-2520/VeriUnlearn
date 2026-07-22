"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import AuthGuard from "../../../components/AuthGuard";
import Navbar from "../../../components/Navbar";
import { api } from "../../../lib/api";

interface Report {
  id: number;
  title: string;
  benchmark_id: number;
  report_format: string;
  content: string;
  created_at: string | null;
}

export default function ReportsPage() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [form, setForm] = useState({ benchmark_id: "", title: "", report_format: "markdown" });

  const { data: reportsData, isLoading, error: listError } = useQuery({
    queryKey: ["research", "reports"],
    queryFn: () => api.research.reports(),
  });

  const reportList: Report[] = Array.isArray(reportsData)
    ? reportsData
    : reportsData?.reports ?? [];

  const selectedReport = reportList.find((r) => r.id === selectedId);

  const generateMutation = useMutation({
    mutationFn: () =>
      api.research.generateReport({
        benchmark_id: parseInt(form.benchmark_id, 10),
        title: form.title,
        report_format: form.report_format,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["research", "reports"] });
      setFormOpen(false);
      setForm({ benchmark_id: "", title: "", report_format: "markdown" });
    },
  });

  function handleExport(report: Report, format: string) {
    const content = format === "json"
      ? JSON.stringify({ title: report.title, format: report.report_format, content: report.content, created_at: report.created_at }, null, 2)
      : report.content;
    const blob = new Blob([content], { type: format === "json" ? "application/json" : "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${report.title.replace(/\s+/g, "_")}.${format === "json" ? "json" : "md"}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <AuthGuard>
      <Navbar />
      <main className="min-h-screen p-8 max-w-7xl mx-auto">
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Reports</h1>
              <p className="text-gray-500 mt-1">Generate and export benchmark analysis reports</p>
            </div>
            <button
              onClick={() => { setFormOpen(!formOpen); setSelectedId(null); }}
              className="bg-primary-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-700"
            >
              {formOpen ? "Cancel" : "Generate Report"}
            </button>
          </div>

          {formOpen && (
            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Generate Report</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Benchmark ID</label>
                  <input
                    type="number"
                    value={form.benchmark_id}
                    onChange={(e) => setForm({ ...form, benchmark_id: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    placeholder="e.g. 1"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
                  <input
                    type="text"
                    value={form.title}
                    onChange={(e) => setForm({ ...form, title: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    placeholder="e.g. Unlearning Benchmark Report"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Format</label>
                  <select
                    value={form.report_format}
                    onChange={(e) => setForm({ ...form, report_format: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white"
                  >
                    <option value="markdown">Markdown</option>
                    <option value="json">JSON</option>
                  </select>
                </div>
              </div>
              <div className="mt-4 flex justify-end">
                <button
                  onClick={() => generateMutation.mutate()}
                  disabled={!form.benchmark_id.trim() || !form.title.trim() || generateMutation.isPending}
                  className="bg-primary-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50"
                >
                  {generateMutation.isPending ? "Generating..." : "Generate"}
                </button>
              </div>
              {generateMutation.isError && (
                <p className="mt-2 text-sm text-red-600">Failed to generate report.</p>
              )}
            </div>
          )}

          {listError && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-5">
              <p className="text-sm text-red-700">Failed to load reports. Please try again later.</p>
            </div>
          )}

          {isLoading ? (
            <div className="rounded-xl border border-gray-200 bg-white p-8">
              <div className="animate-pulse space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-16 bg-gray-100 rounded-lg" />
                ))}
              </div>
            </div>
          ) : reportList.length === 0 ? (
            <div className="rounded-xl border border-gray-200 bg-white p-12 text-center">
              <p className="text-gray-500 text-lg font-medium">No reports yet</p>
              <p className="text-gray-400 text-sm mt-1">Generate a report to analyze benchmark results</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {reportList.map((report) => (
                <button
                  key={report.id}
                  onClick={() => { setSelectedId(report.id); setFormOpen(false); }}
                  className={`rounded-xl border p-5 text-left transition-all ${
                    selectedId === report.id
                      ? "border-primary-300 bg-primary-50 ring-1 ring-primary-200"
                      : "border-gray-200 bg-white hover:shadow-sm"
                  }`}
                >
                  <h3 className="text-base font-semibold text-gray-900">{report.title}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 font-medium">
                      {report.report_format}
                    </span>
                    <span className="text-xs text-gray-400">Benchmark #{report.benchmark_id}</span>
                  </div>
                  {report.created_at && (
                    <p className="text-xs text-gray-400 mt-2">{new Date(report.created_at).toLocaleDateString()}</p>
                  )}
                </button>
              ))}
            </div>
          )}

          {selectedReport && (
            <div className="rounded-xl border border-gray-200 bg-white">
              <div className="px-5 py-4 border-b border-gray-200 flex items-center justify-between">
                <div>
                  <h2 className="font-semibold text-gray-900">{selectedReport.title}</h2>
                  <p className="text-xs text-gray-500 mt-0.5">
                    Format: {selectedReport.report_format} &middot; Benchmark #{selectedReport.benchmark_id}
                    {selectedReport.created_at && (
                      <> &middot; {new Date(selectedReport.created_at).toLocaleString()}</>
                    )}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleExport(selectedReport, "json")}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium border border-gray-200 bg-white hover:bg-gray-50 text-gray-700"
                  >
                    Export JSON
                  </button>
                  <button
                    onClick={() => handleExport(selectedReport, "md")}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium border border-gray-200 bg-white hover:bg-gray-50 text-gray-700"
                  >
                    Export Markdown
                  </button>
                </div>
              </div>
              <div className="p-5">
                {selectedReport.content ? (
                  <pre className="text-sm text-gray-700 bg-gray-50 rounded-lg p-4 overflow-x-auto whitespace-pre-wrap font-mono max-h-96 overflow-y-auto">
                    {selectedReport.content.length > 2000
                      ? selectedReport.content.slice(0, 2000) + "\n\n... (truncated)"
                      : selectedReport.content}
                  </pre>
                ) : (
                  <p className="text-gray-400 text-sm text-center py-6">No content available.</p>
                )}
              </div>
            </div>
          )}
        </div>
      </main>
    </AuthGuard>
  );
}
