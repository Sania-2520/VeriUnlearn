"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import AuthGuard from "../../components/AuthGuard";
import Navbar from "../../components/Navbar";

interface DeletionRequest {
  id: number;
  user_id: number;
  model_version_id: number | null;
  dataset_id: number | null;
  status: string;
  algorithm: string;
  deletion_mode: string;
  reason: string | null;
  compliance_rule: string | null;
  priority: string;
  progress: number;
  requested_records_count: number;
  validation_status: string;
  validation_errors: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
  updated_at: string | null;
  completed_at: string | null;
}

interface UnlearningJob {
  id: number;
  request_id: number;
  user_id: number;
  status: string;
  progress: number;
  current_step: string | null;
  total_steps: number;
  algorithm: string;
  started_at: string | null;
  completed_at: string | null;
  retry_count: number;
  max_retries: number;
  error_message: string | null;
  logs: string | null;
  model_version_before_id: number | null;
  model_version_after_id: number | null;
  created_at: string;
  updated_at: string | null;
}

interface JobStats {
  total: number;
  created: number;
  running: number;
  completed: number;
  failed: number;
  cancelled: number;
  success_rate: number;
}

const authHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem("access_token")}`,
  "Content-Type": "application/json",
});

function statusColor(status: string): string {
  switch (status) {
    case "completed": return "bg-green-100 text-green-700";
    case "validated": return "bg-blue-100 text-blue-700";
    case "running": return "bg-blue-100 text-blue-700";
    case "queued": return "bg-yellow-100 text-yellow-700";
    case "pending": return "bg-yellow-100 text-yellow-700";
    case "created": return "bg-gray-100 text-gray-600";
    case "failed": return "bg-red-100 text-red-700";
    case "cancelled": return "bg-gray-100 text-gray-500";
    case "validation_failed": return "bg-orange-100 text-orange-700";
    case "rollback": return "bg-purple-100 text-purple-700";
    default: return "bg-gray-100 text-gray-500";
  }
}

function priorityColor(p: string): string {
  switch (p) {
    case "urgent": return "bg-red-100 text-red-700";
    case "high": return "bg-orange-100 text-orange-700";
    case "medium": return "bg-blue-100 text-blue-700";
    case "low": return "bg-gray-100 text-gray-500";
    default: return "bg-gray-100 text-gray-500";
  }
}

function formatDate(d: string | null): string {
  if (!d) return "-";
  return new Date(d).toLocaleString();
}

const STEPS = ["created", "validating", "checkpointing", "selecting_algorithm", "executing_unlearning", "verifying", "completed"];

export default function UnlearningPage() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<"requests" | "jobs" | "metrics">("requests");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterPriority, setFilterPriority] = useState("");
  const [expandedRequest, setExpandedRequest] = useState<number | null>(null);
  const [expandedJob, setExpandedJob] = useState<number | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createForm, setCreateForm] = useState({
    model_version_id: "",
    dataset_id: "",
    sample_ids: "",
    deletion_mode: "multiple_samples",
    reason: "",
    compliance_rule: "",
    priority: "medium",
  });

  const { data: requestsData, isLoading: loadingRequests } = useQuery({
    queryKey: ["deletionRequests", filterStatus, filterPriority],
    queryFn: async () => {
      const params = new URLSearchParams({ page_size: "50" });
      if (filterStatus) params.set("status", filterStatus);
      if (filterPriority) params.set("priority", filterPriority);
      const res = await fetch(`/api/v2/unlearning/requests?${params}`, { headers: authHeaders() });
      if (!res.ok) throw new Error("Failed");
      return res.json();
    },
  });

  const { data: jobsData, isLoading: loadingJobs } = useQuery({
    queryKey: ["unlearningJobs", filterStatus],
    queryFn: async () => {
      const params = new URLSearchParams({ page_size: "50" });
      if (filterStatus) params.set("status", filterStatus);
      const res = await fetch(`/api/v2/unlearning/jobs?${params}`, { headers: authHeaders() });
      if (!res.ok) throw new Error("Failed");
      return res.json();
    },
  });

  const { data: stats } = useQuery<JobStats>({
    queryKey: ["unlearningStats"],
    queryFn: async () => {
      const res = await fetch("/api/v2/unlearning/jobs/stats", { headers: authHeaders() });
      if (!res.ok) throw new Error("Failed");
      return res.json();
    },
  });

  const { data: metricsData } = useQuery({
    queryKey: ["unlearningMetrics"],
    queryFn: async () => {
      const res = await fetch("/api/v2/unlearning/metrics", { headers: authHeaders() });
      if (!res.ok) throw new Error("Failed");
      return res.json();
    },
  });

  const { data: auditData } = useQuery({
    queryKey: ["auditEvents"],
    queryFn: async () => {
      const res = await fetch("/api/v2/unlearning/audit?limit=30", { headers: authHeaders() });
      if (!res.ok) throw new Error("Failed");
      return res.json();
    },
  });

  const createMutation = useMutation({
    mutationFn: async (body: Record<string, unknown>) => {
      const res = await fetch("/api/v2/unlearning/requests", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to create request");
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["deletionRequests"] });
      setShowCreateModal(false);
    },
  });

  const executeMutation = useMutation({
    mutationFn: async (requestId: number) => {
      const res = await fetch(`/api/v2/unlearning/requests/${requestId}/execute`, {
        method: "POST",
        headers: authHeaders(),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed");
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["deletionRequests"] });
      queryClient.invalidateQueries({ queryKey: ["unlearningJobs"] });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: async (requestId: number) => {
      const res = await fetch(`/api/v2/unlearning/requests/${requestId}/cancel`, {
        method: "POST",
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error("Failed");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["deletionRequests"] });
    },
  });

  const requests: DeletionRequest[] = requestsData?.requests || [];
  const jobs: UnlearningJob[] = jobsData?.jobs || [];

  return (
    <AuthGuard>
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 pt-20">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Unlearning Engine</h1>
            <p className="text-sm text-gray-500 mt-1">Manage deletion requests, unlearning jobs, and model verification</p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            New Deletion Request
          </button>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mb-6">
            {[
              { label: "Total", value: stats.total, color: "text-gray-900" },
              { label: "Running", value: stats.running, color: "text-blue-600" },
              { label: "Completed", value: stats.completed, color: "text-green-600" },
              { label: "Failed", value: stats.failed, color: "text-red-600" },
              { label: "Cancelled", value: stats.cancelled, color: "text-gray-500" },
              { label: "Success Rate", value: `${stats.success_rate}%`, color: "text-primary-600" },
            ].map((s) => (
              <div key={s.label} className="rounded-xl border border-gray-200 bg-white p-4">
                <p className="text-xs text-gray-500">{s.label}</p>
                <p className={`text-xl font-bold mt-1 ${s.color}`}>{s.value}</p>
              </div>
            ))}
          </div>
        )}

        {/* Tabs */}
        <div className="flex space-x-1 bg-gray-100 rounded-lg p-1 mb-6 w-fit">
          {(["requests", "jobs", "metrics"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 text-sm rounded-md transition-colors ${
                tab === t ? "bg-white shadow-sm text-gray-900 font-medium" : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {t === "requests" ? "Deletion Requests" : t === "jobs" ? "Unlearning Jobs" : "Metrics & Audit"}
            </button>
          ))}
        </div>

        {/* Filter Bar */}
        <div className="flex items-center space-x-2 mb-4">
          {["", "pending", "validated", "running", "completed", "failed", "cancelled"].map((s) => (
            <button
              key={s}
              onClick={() => setFilterStatus(s)}
              className={`px-3 py-1.5 text-sm rounded-lg border ${
                filterStatus === s
                  ? "bg-primary-50 border-primary-300 text-primary-700"
                  : "border-gray-200 text-gray-500 hover:bg-gray-50"
              }`}
            >
              {s || "All"}
            </button>
          ))}
          {tab === "requests" && (
            <>
              <span className="text-gray-300 mx-1">|</span>
              {["", "low", "medium", "high", "urgent"].map((p) => (
                <button
                  key={p}
                  onClick={() => setFilterPriority(p)}
                  className={`px-3 py-1.5 text-sm rounded-lg border ${
                    filterPriority === p
                      ? "bg-primary-50 border-primary-300 text-primary-700"
                      : "border-gray-200 text-gray-500 hover:bg-gray-50"
                  }`}
                >
                  {p || "Any Priority"}
                </button>
              ))}
            </>
          )}
        </div>

        {/* Tab: Deletion Requests */}
        {tab === "requests" && (
          <div className="space-y-3">
            {loadingRequests ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="rounded-xl border border-gray-200 bg-white p-5 animate-pulse">
                    <div className="h-4 bg-gray-200 rounded w-1/3 mb-3" />
                    <div className="h-3 bg-gray-200 rounded w-2/3" />
                  </div>
                ))}
              </div>
            ) : requests.length === 0 ? (
              <div className="rounded-xl border border-gray-200 bg-white p-12 text-center">
                <p className="text-gray-500 text-lg font-medium">No deletion requests yet</p>
                <p className="text-gray-400 text-sm mt-1">Create a deletion request to start the unlearning process</p>
              </div>
            ) : (
              requests.map((req) => (
                <div
                  key={req.id}
                  className="rounded-xl border border-gray-200 bg-white overflow-hidden"
                >
                  <div
                    className="p-5 cursor-pointer hover:bg-gray-50"
                    onClick={() => setExpandedRequest(expandedRequest === req.id ? null : req.id)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <span className="text-sm font-mono text-gray-400">#{req.id}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(req.status)}`}>
                          {req.status}
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${priorityColor(req.priority)}`}>
                          {req.priority}
                        </span>
                        <span className="text-xs text-gray-500">{req.deletion_mode}</span>
                        {req.algorithm !== "auto" && (
                          <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">{req.algorithm}</span>
                        )}
                      </div>
                      <div className="flex items-center space-x-3">
                        <span className="text-xs text-gray-400">{formatDate(req.created_at)}</span>
                        {req.status === "validated" && (
                          <button
                            onClick={(e) => { e.stopPropagation(); executeMutation.mutate(req.id); }}
                            className="px-3 py-1 text-xs bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                          >
                            Execute
                          </button>
                        )}
                        {["pending", "validated", "queued"].includes(req.status) && (
                          <button
                            onClick={(e) => { e.stopPropagation(); cancelMutation.mutate(req.id); }}
                            className="px-3 py-1 text-xs bg-red-50 text-red-600 rounded-lg hover:bg-red-100"
                          >
                            Cancel
                          </button>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                      <span>{req.requested_records_count} records</span>
                      {req.compliance_rule && <span>Compliance: {req.compliance_rule}</span>}
                      {req.model_version_id && <span>Model v{req.model_version_id}</span>}
                      {req.dataset_id && <span>Dataset {req.dataset_id}</span>}
                      <span className={`ml-auto ${req.validation_status === "passed" ? "text-green-600" : req.validation_status === "failed" ? "text-red-600" : "text-yellow-600"}`}>
                        Validation: {req.validation_status}
                      </span>
                    </div>
                    {req.status !== "pending" && (
                      <div className="mt-3">
                        <div className="flex justify-between text-xs text-gray-500 mb-1">
                          <span>Progress</span>
                          <span>{Math.round(req.progress * 100)}%</span>
                        </div>
                        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary-500 rounded-full transition-all"
                            style={{ width: `${req.progress * 100}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </div>

                  {expandedRequest === req.id && (
                    <div className="border-t border-gray-100 p-5 bg-gray-50">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <p className="text-gray-500 text-xs">Request ID</p>
                          <p className="font-medium">{req.id}</p>
                        </div>
                        <div>
                          <p className="text-gray-500 text-xs">Algorithm</p>
                          <p className="font-medium">{req.algorithm}</p>
                        </div>
                        <div>
                          <p className="text-gray-500 text-xs">Deletion Mode</p>
                          <p className="font-medium">{req.deletion_mode}</p>
                        </div>
                        <div>
                          <p className="text-gray-500 text-xs">Reason</p>
                          <p className="font-medium">{req.reason || "-"}</p>
                        </div>
                        <div>
                          <p className="text-gray-500 text-xs">Created</p>
                          <p className="font-medium">{formatDate(req.created_at)}</p>
                        </div>
                        <div>
                          <p className="text-gray-500 text-xs">Completed</p>
                          <p className="font-medium">{formatDate(req.completed_at)}</p>
                        </div>
                        <div>
                          <p className="text-gray-500 text-xs">Error</p>
                          <p className="font-medium text-red-600">{req.error_message || "-"}</p>
                        </div>
                        <div>
                          <p className="text-gray-500 text-xs">Validation Errors</p>
                          <p className="font-medium">
                            {req.validation_errors ? JSON.stringify(req.validation_errors) : "-"}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {/* Tab: Unlearning Jobs */}
        {tab === "jobs" && (
          <div className="space-y-3">
            {loadingJobs ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="rounded-xl border border-gray-200 bg-white p-5 animate-pulse">
                    <div className="h-4 bg-gray-200 rounded w-1/3 mb-3" />
                    <div className="h-3 bg-gray-200 rounded w-2/3" />
                  </div>
                ))}
              </div>
            ) : jobs.length === 0 ? (
              <div className="rounded-xl border border-gray-200 bg-white p-12 text-center">
                <p className="text-gray-500 text-lg font-medium">No unlearning jobs yet</p>
                <p className="text-gray-400 text-sm mt-1">Jobs appear here after executing a deletion request</p>
              </div>
            ) : (
              jobs.map((job) => (
                <div
                  key={job.id}
                  className="rounded-xl border border-gray-200 bg-white overflow-hidden"
                >
                  <div
                    className="p-5 cursor-pointer hover:bg-gray-50"
                    onClick={() => setExpandedJob(expandedJob === job.id ? null : job.id)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <span className="text-sm font-mono text-gray-400">Job #{job.id}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(job.status)}`}>
                          {job.status}
                        </span>
                        <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">{job.algorithm}</span>
                        <span className="text-xs text-gray-500">Request #{job.request_id}</span>
                      </div>
                      <span className="text-xs text-gray-400">{formatDate(job.created_at)}</span>
                    </div>

                    {/* Step Progress */}
                    <div className="mt-4">
                      <div className="flex items-center space-x-1">
                        {STEPS.map((step, idx) => {
                          const stepIdx = STEPS.indexOf(job.current_step || "created");
                          const isDone = idx < stepIdx;
                          const isCurrent = idx === stepIdx;
                          return (
                            <div key={step} className="flex-1">
                              <div className={`h-1.5 rounded-full ${
                                isDone ? "bg-green-500" : isCurrent ? "bg-primary-500" : "bg-gray-200"
                              }`} />
                              <p className={`text-[10px] mt-1 ${isCurrent ? "text-primary-600 font-medium" : "text-gray-400"}`}>
                                {step.replace(/_/g, " ")}
                              </p>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    <div className="mt-3">
                      <div className="flex justify-between text-xs text-gray-500 mb-1">
                        <span>{job.current_step?.replace(/_/g, " ") || "idle"}</span>
                        <span>{Math.round(job.progress * 100)}%</span>
                      </div>
                      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary-500 rounded-full transition-all"
                          style={{ width: `${job.progress * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  {expandedJob === job.id && (
                    <div className="border-t border-gray-100 p-5 bg-gray-50">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-4">
                        <div>
                          <p className="text-gray-500 text-xs">Model Before</p>
                          <p className="font-medium">v{job.model_version_before_id || "-"}</p>
                        </div>
                        <div>
                          <p className="text-gray-500 text-xs">Model After</p>
                          <p className="font-medium">v{job.model_version_after_id || "-"}</p>
                        </div>
                        <div>
                          <p className="text-gray-500 text-xs">Retries</p>
                          <p className="font-medium">{job.retry_count} / {job.max_retries}</p>
                        </div>
                        <div>
                          <p className="text-gray-500 text-xs">Duration</p>
                          <p className="font-medium">
                            {job.started_at && job.completed_at
                              ? `${Math.round((new Date(job.completed_at).getTime() - new Date(job.started_at).getTime()) / 1000)}s`
                              : job.started_at ? "running..." : "-"}
                          </p>
                        </div>
                      </div>
                      {job.logs && (
                        <div>
                          <p className="text-xs font-medium text-gray-500 mb-2">Logs</p>
                          <pre className="text-xs bg-gray-900 text-green-400 rounded-lg p-3 overflow-x-auto max-h-48 overflow-y-auto">
                            {job.logs}
                          </pre>
                        </div>
                      )}
                      {job.error_message && (
                        <div className="mt-3">
                          <p className="text-xs font-medium text-red-500 mb-1">Error</p>
                          <p className="text-xs text-red-600 bg-red-50 p-2 rounded-lg">{job.error_message}</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {/* Tab: Metrics & Audit */}
        {tab === "metrics" && (
          <div className="space-y-6">
            {/* Metrics Summary */}
            <div className="rounded-xl border border-gray-200 bg-white p-5">
              <h3 className="text-sm font-medium text-gray-700 mb-4">Unlearning Metrics Summary</h3>
              {metricsData?.summary ? (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { label: "Total Runs", value: metricsData.summary.total_runs },
                    { label: "Avg Execution Time", value: `${metricsData.summary.avg_execution_time}s` },
                    { label: "Avg Utility Retention", value: `${(metricsData.summary.avg_utility_retention * 100).toFixed(1)}%` },
                    { label: "Avg Forget Quality", value: `${(metricsData.summary.avg_forget_quality * 100).toFixed(1)}%` },
                  ].map((m) => (
                    <div key={m.label}>
                      <p className="text-xs text-gray-500">{m.label}</p>
                      <p className="text-lg font-bold text-gray-900">{m.value}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-400">No metrics available yet</p>
              )}
            </div>

            {/* Audit Trail */}
            <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
              <div className="p-5 border-b border-gray-100">
                <h3 className="text-sm font-medium text-gray-700">Audit Trail</h3>
              </div>
              <div className="divide-y divide-gray-100">
                {(auditData?.events || []).length === 0 ? (
                  <div className="p-8 text-center text-sm text-gray-400">No audit events yet</div>
                ) : (
                  (auditData?.events || []).map((event: { id: number; event_type: string; event_data: Record<string, unknown>; created_at: string; user_id: number | null }) => (
                    <div key={event.id} className="px-5 py-3 flex items-center justify-between text-sm">
                      <div className="flex items-center space-x-3">
                        <span className="w-2 h-2 rounded-full bg-primary-500" />
                        <span className="font-medium text-gray-700">{event.event_type}</span>
                        <span className="text-xs text-gray-400">
                          {Object.entries(event.event_data || {}).map(([k, v]) => `${k}=${String(v)}`).join(", ")}
                        </span>
                      </div>
                      <span className="text-xs text-gray-400">{formatDate(event.created_at)}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* Create Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl p-6 w-full max-w-lg space-y-4 max-h-[90vh] overflow-y-auto">
              <h3 className="text-lg font-semibold text-gray-900">New Deletion Request</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Model Version ID *</label>
                  <input
                    type="number"
                    value={createForm.model_version_id}
                    onChange={(e) => setCreateForm({ ...createForm, model_version_id: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                    placeholder="1"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Dataset ID *</label>
                  <input
                    type="number"
                    value={createForm.dataset_id}
                    onChange={(e) => setCreateForm({ ...createForm, dataset_id: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                    placeholder="1"
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Sample IDs (comma-separated)</label>
                  <input
                    type="text"
                    value={createForm.sample_ids}
                    onChange={(e) => setCreateForm({ ...createForm, sample_ids: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                    placeholder="1, 2, 3"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Deletion Mode</label>
                  <select
                    value={createForm.deletion_mode}
                    onChange={(e) => setCreateForm({ ...createForm, deletion_mode: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="single_sample">Single Sample</option>
                    <option value="multiple_samples">Multiple Samples</option>
                    <option value="entire_user">Entire User</option>
                    <option value="entire_dataset_partition">Dataset Partition</option>
                    <option value="entire_dataset">Entire Dataset</option>
                    <option value="bulk">Bulk</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                  <select
                    value={createForm.priority}
                    onChange={(e) => setCreateForm({ ...createForm, priority: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Compliance Rule</label>
                  <select
                    value={createForm.compliance_rule}
                    onChange={(e) => setCreateForm({ ...createForm, compliance_rule: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="">None</option>
                    <option value="GDPR">GDPR</option>
                    <option value="CCPA">CCPA</option>
                    <option value="PIPA">PIPA</option>
                    <option value="LGPD">LGPD</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Algorithm</label>
                  <select
                    value={createForm.deletion_mode === "entire_dataset" ? "auto" : ""}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                    disabled
                  >
                    <option value="auto">Auto (Adaptive)</option>
                  </select>
                  <p className="text-xs text-gray-400 mt-1">Algorithm is automatically selected</p>
                </div>
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Reason</label>
                  <textarea
                    value={createForm.reason}
                    onChange={(e) => setCreateForm({ ...createForm, reason: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                    rows={2}
                    placeholder="e.g. GDPR right to be forgotten request from user #12345"
                  />
                </div>
              </div>
              {createMutation.isError && (
                <p className="text-sm text-red-600 bg-red-50 p-2 rounded-lg">{createMutation.error.message}</p>
              )}
              <div className="flex justify-end space-x-3 pt-2">
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    const sampleIds = createForm.sample_ids
                      ? createForm.sample_ids.split(",").map((s) => parseInt(s.trim(), 10)).filter((n) => !isNaN(n))
                      : [];
                    createMutation.mutate({
                      model_version_id: parseInt(createForm.model_version_id, 10),
                      dataset_id: parseInt(createForm.dataset_id, 10),
                      sample_ids: sampleIds,
                      deletion_mode: createForm.deletion_mode,
                      reason: createForm.reason || undefined,
                      compliance_rule: createForm.compliance_rule || undefined,
                      priority: createForm.priority,
                    });
                  }}
                  disabled={createMutation.isPending || !createForm.model_version_id || !createForm.dataset_id}
                  className="px-4 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                >
                  {createMutation.isPending ? "Creating..." : "Create Request"}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </AuthGuard>
  );
}
