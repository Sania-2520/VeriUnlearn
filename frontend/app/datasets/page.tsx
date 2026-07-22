"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import AuthGuard from "../../components/AuthGuard";
import Navbar from "../../components/Navbar";

interface Dataset {
  id: number;
  name: string;
  description: string | null;
  status: string;
  dataset_type: string;
  filename: string;
  file_size: number;
  record_count: number;
  version: number;
  file_hash: string;
  schema_info: { columns?: { name: string; type: string }[] } | null;
  created_at: string;
  updated_at: string | null;
}

interface PreviewData {
  headers: string[];
  rows: string[][];
  total_rows: number;
  preview_rows: number;
}

const authHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem("access_token")}`,
});

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(d: string): string {
  return new Date(d).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function DatasetsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [page, setPage] = useState(1);
  const [selectedDataset, setSelectedDataset] = useState<number | null>(null);
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [uploadName, setUploadName] = useState("");
  const [uploadDesc, setUploadDesc] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);
  const [showPreview, setShowPreview] = useState(false);

  const { data: datasetsData, isLoading } = useQuery({
    queryKey: ["datasets", page, search, filterType, filterStatus],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), page_size: "12" });
      if (search) params.set("search", search);
      if (filterType) params.set("dataset_type", filterType);
      if (filterStatus) params.set("status", filterStatus);
      const res = await fetch(`/api/datasets/?${params}`, { headers: authHeaders() });
      if (!res.ok) throw new Error("Failed to fetch datasets");
      return res.json();
    },
  });

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!uploadFile || !uploadName) throw new Error("Missing data");
      const formData = new FormData();
      formData.append("file", uploadFile);
      const params = new URLSearchParams({ name: uploadName });
      if (uploadDesc) params.set("description", uploadDesc);
      const res = await fetch(`/api/datasets/upload?${params}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` },
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Upload failed");
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["datasets"] });
      setShowUploadDialog(false);
      setUploadName("");
      setUploadDesc("");
      setUploadFile(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      const res = await fetch(`/api/datasets/${id}`, {
        method: "DELETE",
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error("Delete failed");
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["datasets"] }),
  });

  const previewMutation = useMutation({
    mutationFn: async (id: number) => {
      const res = await fetch(`/api/datasets/${id}/preview`, { headers: authHeaders() });
      if (!res.ok) throw new Error("Preview failed");
      return res.json();
    },
    onSuccess: (data: PreviewData) => {
      setPreviewData(data);
      setShowPreview(true);
    },
  });

  const datasets: Dataset[] = datasetsData?.datasets ?? [];
  const total: number = datasetsData?.total ?? 0;

  return (
    <AuthGuard>
      <Navbar />
      <main className="min-h-screen p-8 max-w-7xl mx-auto">
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Datasets</h1>
              <p className="text-gray-500 mt-1">Upload, version, and manage training datasets</p>
            </div>
            <button
              onClick={() => setShowUploadDialog(true)}
              className="bg-primary-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors"
            >
              Upload Dataset
            </button>
          </div>

          <div className="flex gap-3 items-center">
            <input
              type="text"
              placeholder="Search datasets..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <select
              value={filterType}
              onChange={(e) => { setFilterType(e.target.value); setPage(1); }}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">All Types</option>
              <option value="csv">CSV</option>
              <option value="json">JSON</option>
              <option value="txt">TXT</option>
              <option value="pdf">PDF</option>
            </select>
            <select
              value={filterStatus}
              onChange={(e) => { setFilterStatus(e.target.value); setPage(1); }}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">All Status</option>
              <option value="ready">Ready</option>
              <option value="uploading">Uploading</option>
              <option value="processing">Processing</option>
              <option value="archived">Archived</option>
            </select>
          </div>

          {showUploadDialog && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
              <div className="bg-white rounded-xl p-6 w-full max-w-md space-y-4">
                <h2 className="text-lg font-semibold text-gray-900">Upload Dataset</h2>
                <input
                  type="text"
                  placeholder="Dataset name"
                  value={uploadName}
                  onChange={(e) => setUploadName(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
                <input
                  type="text"
                  placeholder="Description (optional)"
                  value={uploadDesc}
                  onChange={(e) => setUploadDesc(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center">
                  <input
                    type="file"
                    accept=".csv,.json,.txt,.jsonl,.pdf,.md"
                    onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                    className="text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100"
                  />
                  {uploadFile && (
                    <p className="mt-2 text-sm text-gray-600">{uploadFile.name} ({formatSize(uploadFile.size)})</p>
                  )}
                </div>
                {uploadMutation.isError && (
                  <p className="text-sm text-red-600 bg-red-50 p-2 rounded-lg">{(uploadMutation.error as Error).message}</p>
                )}
                <div className="flex gap-3 justify-end">
                  <button
                    onClick={() => { setShowUploadDialog(false); setUploadFile(null); }}
                    className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => uploadMutation.mutate()}
                    disabled={!uploadName || !uploadFile || uploadMutation.isPending}
                    className="px-4 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                  >
                    {uploadMutation.isPending ? "Uploading..." : "Upload"}
                  </button>
                </div>
              </div>
            </div>
          )}

          {showPreview && previewData && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
              <div className="bg-white rounded-xl p-6 w-full max-w-4xl max-h-[80vh] overflow-auto">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold text-gray-900">Dataset Preview</h2>
                  <button onClick={() => setShowPreview(false)} className="text-gray-400 hover:text-gray-600">&times;</button>
                </div>
                <p className="text-sm text-gray-500 mb-3">Showing {previewData.preview_rows} of {previewData.total_rows} rows</p>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm border border-gray-200">
                    <thead>
                      <tr className="bg-gray-50">
                        {previewData.headers.map((h, i) => (
                          <th key={i} className="px-3 py-2 text-left font-medium text-gray-600 border-b">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {previewData.rows.map((row, ri) => (
                        <tr key={ri} className="border-b border-gray-100">
                          {row.map((cell, ci) => (
                            <td key={ci} className="px-3 py-2 text-gray-900 max-w-[200px] truncate">{cell}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="rounded-xl border border-gray-200 bg-white p-5 animate-pulse">
                  <div className="h-5 bg-gray-200 rounded w-1/2 mb-3"></div>
                  <div className="h-4 bg-gray-100 rounded w-3/4 mb-2"></div>
                  <div className="h-4 bg-gray-100 rounded w-1/4"></div>
                </div>
              ))}
            </div>
          ) : datasets.length === 0 ? (
            <div className="rounded-xl border border-gray-200 bg-white p-12 text-center">
              <div className="text-gray-400 text-4xl mb-3">&#128202;</div>
              <p className="text-gray-500 text-lg font-medium">No datasets yet</p>
              <p className="text-gray-400 text-sm mt-1">Upload a CSV, JSON, TXT, or PDF file to get started</p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {datasets.map((ds) => (
                  <div key={ds.id} className="rounded-xl border border-gray-200 bg-white p-5 hover:shadow-sm transition-shadow">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1 min-w-0">
                        <h3 className="font-medium text-gray-900 truncate">{ds.name}</h3>
                        {ds.description && <p className="text-sm text-gray-400 truncate mt-0.5">{ds.description}</p>}
                      </div>
                      <span className={`text-xs px-2 py-0.5 rounded-full ml-2 shrink-0 ${
                        ds.status === "ready" ? "bg-green-100 text-green-700" :
                        ds.status === "uploading" ? "bg-blue-100 text-blue-700" :
                        ds.status === "archived" ? "bg-gray-100 text-gray-500" :
                        "bg-yellow-100 text-yellow-700"
                      }`}>
                        {ds.status}
                      </span>
                    </div>
                    <div className="space-y-1.5 text-sm text-gray-500">
                      <div className="flex justify-between">
                        <span>Type</span>
                        <span className="text-gray-700 font-mono text-xs uppercase">{ds.dataset_type}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Records</span>
                        <span className="text-gray-700">{ds.record_count.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Size</span>
                        <span className="text-gray-700">{formatSize(ds.file_size)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Version</span>
                        <span className="text-gray-700">v{ds.version}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>SHA256</span>
                        <span className="text-gray-700 font-mono text-xs">{ds.file_hash.substring(0, 12)}...</span>
                      </div>
                    </div>
                    {ds.schema_info?.columns && (
                      <div className="mt-3 pt-3 border-t border-gray-100">
                        <p className="text-xs text-gray-400 mb-1">Schema ({ds.schema_info.columns.length} columns)</p>
                        <div className="flex flex-wrap gap-1">
                          {ds.schema_info.columns.slice(0, 4).map((col, i) => (
                            <span key={i} className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">{col.name}</span>
                          ))}
                          {ds.schema_info.columns.length > 4 && (
                            <span className="text-xs text-gray-400">+{ds.schema_info.columns.length - 4}</span>
                          )}
                        </div>
                      </div>
                    )}
                    <div className="mt-3 pt-3 border-t border-gray-100 flex gap-2">
                      <button
                        onClick={() => previewMutation.mutate(ds.id)}
                        className="text-xs text-primary-600 hover:text-primary-700 font-medium"
                      >
                        Preview
                      </button>
                      <button
                        onClick={() => deleteMutation.mutate(ds.id)}
                        className="text-xs text-red-500 hover:text-red-600 font-medium ml-auto"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
              {total > 12 && (
                <div className="flex justify-center gap-2 mt-4">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <span className="px-3 py-1.5 text-sm text-gray-500">
                    Page {page} of {Math.ceil(total / 12)}
                  </span>
                  <button
                    onClick={() => setPage((p) => p + 1)}
                    disabled={page >= Math.ceil(total / 12)}
                    className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </main>
    </AuthGuard>
  );
}
