"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import AuthGuard from "../../components/AuthGuard";
import Navbar from "../../components/Navbar";

interface VerificationJob {
  id: number;
  request_id: number;
  job_id: number | null;
  status: string;
  current_step: string | null;
  total_steps: number;
  progress: number;
  trust_score: number | null;
  overall_status: string | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  model_version_before_id: number | null;
  model_version_after_id: number | null;
  created_at: string;
}

interface VerificationResult {
  id: number;
  algorithm: string;
  status: string;
  confidence_score: number;
  trust_score: number;
  metrics: Record<string, unknown> | null;
  execution_time_ms: number;
  created_at: string;
}

interface Certificate {
  id: number;
  certificate_id: string;
  job_id: number;
  request_id: number;
  verification_result: string;
  trust_score: number;
  confidence_score: number;
  algorithm_used: string;
  model_before_hash: string | null;
  model_after_hash: string | null;
  merkle_root: string | null;
  signature: string | null;
  integrity_hash: string | null;
  created_at: string;
}

interface JobStats {
  total: number;
  completed: number;
  passed: number;
  failed: number;
  pass_rate: number;
}

const authHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem("access_token")}`,
  "Content-Type": "application/json",
});

function statusColor(s: string): string {
  switch (s) {
    case "completed": return "bg-green-100 text-green-700";
    case "passed": return "bg-green-100 text-green-700";
    case "running": return "bg-blue-100 text-blue-700";
    case "pending": return "bg-yellow-100 text-yellow-700";
    case "failed": return "bg-red-100 text-red-700";
    default: return "bg-gray-100 text-gray-500";
  }
}

function trustColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-yellow-600";
  return "text-red-600";
}

function formatDate(d: string | null): string {
  if (!d) return "-";
  return new Date(d).toLocaleString();
}

const VERIFICATION_STEPS = ["hash_verification", "merkle_verification", "influence_verification", "membership_inference", "forget_quality"];

export default function VerificationPage() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<"jobs" | "certificates" | "trust">("jobs");
  const [expandedJob, setExpandedJob] = useState<number | null>(null);
  const [selectedJob, setSelectedJob] = useState<number | null>(null);

  const { data: jobsData, isLoading: loadingJobs } = useQuery({
    queryKey: ["verificationJobs"],
    queryFn: async () => {
      const res = await fetch("/api/v2/verification/jobs?page_size=50", { headers: authHeaders() });
      if (!res.ok) throw new Error("Failed");
      return res.json();
    },
  });

  const { data: stats } = useQuery<JobStats>({
    queryKey: ["verificationStats"],
    queryFn: async () => {
      const res = await fetch("/api/v2/verification/jobs/stats", { headers: authHeaders() });
      if (!res.ok) throw new Error("Failed");
      return res.json();
    },
  });

  const { data: certsData } = useQuery({
    queryKey: ["certificates"],
    queryFn: async () => {
      const res = await fetch("/api/v2/verification/certificates?page_size=50", { headers: authHeaders() });
      if (!res.ok) throw new Error("Failed");
      return res.json();
    },
  });

  const { data: resultsData } = useQuery({
    queryKey: ["verificationResults", selectedJob],
    queryFn: async () => {
      if (!selectedJob) return null;
      const res = await fetch(`/api/v2/verification/jobs/${selectedJob}/results`, { headers: authHeaders() });
      if (!res.ok) throw new Error("Failed");
      return res.json();
    },
    enabled: !!selectedJob,
  });

  const { data: trustData } = useQuery({
    queryKey: ["trustScore", selectedJob],
    queryFn: async () => {
      if (!selectedJob) return null;
      const res = await fetch(`/api/v2/verification/jobs/${selectedJob}/trust`, { headers: authHeaders() });
      if (!res.ok) return null;
      return res.json();
    },
    enabled: !!selectedJob,
  });

  const { data: reportData } = useQuery({
    queryKey: ["verificationReport", selectedJob],
    queryFn: async () => {
      if (!selectedJob) return null;
      const res = await fetch(`/api/v2/verification/jobs/${selectedJob}/report`, { headers: authHeaders() });
      if (!res.ok) return null;
      return res.json();
    },
    enabled: !!selectedJob,
  });

  const validateMutation = useMutation({
    mutationFn: async (certId: string) => {
      const res = await fetch(`/api/v2/verification/certificates/${certId}/validate`, { headers: authHeaders() });
      if (!res.ok) throw new Error("Validation failed");
      return res.json();
    },
  });

  const jobs: VerificationJob[] = jobsData?.jobs || [];
  const certificates: Certificate[] = certsData?.certificates || [];
  const results: VerificationResult[] = resultsData?.results || [];

  return (
    <AuthGuard>
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 pt-20">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Verification Engine</h1>
            <p className="text-sm text-gray-500 mt-1">Cryptographic proof, certificates, and trust scoring</p>
          </div>
        </div>

        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
            {[
              { label: "Total Verifications", value: stats.total, color: "text-gray-900" },
              { label: "Completed", value: stats.completed, color: "text-blue-600" },
              { label: "Passed", value: stats.passed, color: "text-green-600" },
              { label: "Failed", value: stats.failed, color: "text-red-600" },
              { label: "Pass Rate", value: `${stats.pass_rate}%`, color: "text-primary-600" },
            ].map((s) => (
              <div key={s.label} className="rounded-xl border border-gray-200 bg-white p-4">
                <p className="text-xs text-gray-500">{s.label}</p>
                <p className={`text-xl font-bold mt-1 ${s.color}`}>{s.value}</p>
              </div>
            ))}
          </div>
        )}

        <div className="flex space-x-1 bg-gray-100 rounded-lg p-1 mb-6 w-fit">
          {(["jobs", "certificates", "trust"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 text-sm rounded-md transition-colors ${
                tab === t ? "bg-white shadow-sm text-gray-900 font-medium" : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {t === "jobs" ? "Verification Jobs" : t === "certificates" ? "Certificates" : "Trust Dashboard"}
            </button>
          ))}
        </div>

        {tab === "jobs" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-3">
              {loadingJobs ? (
                [1, 2, 3].map((i) => (
                  <div key={i} className="rounded-xl border border-gray-200 bg-white p-5 animate-pulse">
                    <div className="h-4 bg-gray-200 rounded w-1/3 mb-3" />
                    <div className="h-3 bg-gray-200 rounded w-2/3" />
                  </div>
                ))
              ) : jobs.length === 0 ? (
                <div className="rounded-xl border border-gray-200 bg-white p-12 text-center">
                  <p className="text-gray-500 text-lg font-medium">No verification jobs yet</p>
                  <p className="text-gray-400 text-sm mt-1">Verifications are triggered automatically after unlearning</p>
                </div>
              ) : (
                jobs.map((job) => (
                  <div
                    key={job.id}
                    className={`rounded-xl border bg-white overflow-hidden cursor-pointer transition-all ${
                      selectedJob === job.id ? "border-primary-400 ring-2 ring-primary-100" : "border-gray-200 hover:border-gray-300"
                    }`}
                    onClick={() => {
                      setSelectedJob(job.id);
                      setExpandedJob(expandedJob === job.id ? null : job.id);
                    }}
                  >
                    <div className="p-5">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          <span className="text-sm font-mono text-gray-400">VER-{job.id}</span>
                          <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(job.status)}`}>{job.status}</span>
                          {job.overall_status && (
                            <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(job.overall_status)}`}>
                              {job.overall_status}
                            </span>
                          )}
                          <span className="text-xs text-gray-500">Request #{job.request_id}</span>
                        </div>
                        <div className="flex items-center space-x-3">
                          {job.trust_score !== null && (
                            <span className={`text-sm font-bold ${trustColor(job.trust_score)}`}>
                              Trust: {job.trust_score}
                            </span>
                          )}
                          <span className="text-xs text-gray-400">{formatDate(job.created_at)}</span>
                        </div>
                      </div>
                      <div className="mt-3">
                        <div className="flex justify-between text-xs text-gray-500 mb-1">
                          <span>{job.current_step?.replace(/_/g, " ") || "idle"}</span>
                          <span>{Math.round(job.progress * 100)}%</span>
                        </div>
                        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div className="h-full bg-primary-500 rounded-full transition-all" style={{ width: `${job.progress * 100}%` }} />
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
                            <p className="text-gray-500 text-xs">Started</p>
                            <p className="font-medium">{formatDate(job.started_at)}</p>
                          </div>
                          <div>
                            <p className="text-gray-500 text-xs">Completed</p>
                            <p className="font-medium">{formatDate(job.completed_at)}</p>
                          </div>
                        </div>
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

            <div className="space-y-4">
              <div className="rounded-xl border border-gray-200 bg-white p-5">
                <h3 className="text-sm font-medium text-gray-700 mb-3">Algorithm Results</h3>
                {results.length === 0 ? (
                  <p className="text-sm text-gray-400">Select a verification job</p>
                ) : (
                  <div className="space-y-2">
                    {results.map((r) => (
                      <div key={r.id} className="flex items-center justify-between text-sm py-2 border-b border-gray-100 last:border-0">
                        <div className="flex items-center space-x-2">
                          <span className={`w-2 h-2 rounded-full ${r.status === "passed" ? "bg-green-500" : "bg-red-500"}`} />
                          <span className="font-medium text-gray-700">{r.algorithm.replace(/_/g, " ")}</span>
                        </div>
                        <div className="text-right">
                          <p className={`font-mono text-xs ${r.status === "passed" ? "text-green-600" : "text-red-600"}`}>
                            {r.status}
                          </p>
                          <p className="text-xs text-gray-400">{(r.confidence_score * 100).toFixed(0)}%</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {trustData && (
                <div className="rounded-xl border border-gray-200 bg-white p-5">
                  <h3 className="text-sm font-medium text-gray-700 mb-3">Trust Score</h3>
                  <div className="text-center mb-4">
                    <p className={`text-4xl font-bold ${trustColor(trustData.overall_score)}`}>
                      {trustData.overall_score}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">out of 100</p>
                  </div>
                  <div className="space-y-2">
                    {[
                      { label: "Verification", value: trustData.verification_score },
                      { label: "Forget Quality", value: trustData.forget_score },
                      { label: "Retention", value: trustData.retention_score },
                      { label: "Privacy", value: trustData.privacy_score },
                      { label: "Integrity", value: trustData.integrity_score },
                    ].map((item) => (
                      <div key={item.label} className="flex justify-between text-xs">
                        <span className="text-gray-500">{item.label}</span>
                        <span className="font-mono text-gray-700">{(item.value * 100).toFixed(0)}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {reportData && reportData.recommendations && (
                <div className="rounded-xl border border-gray-200 bg-white p-5">
                  <h3 className="text-sm font-medium text-gray-700 mb-3">Recommendations</h3>
                  <div className="space-y-2">
                    {reportData.recommendations.map((rec: string, i: number) => (
                      <div key={i} className="flex items-start space-x-2 text-xs text-gray-600">
                        <span className="text-primary-500 mt-0.5">•</span>
                        <span>{rec}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {tab === "certificates" && (
          <div className="space-y-3">
            {certificates.length === 0 ? (
              <div className="rounded-xl border border-gray-200 bg-white p-12 text-center">
                <p className="text-gray-500 text-lg font-medium">No certificates yet</p>
                <p className="text-gray-400 text-sm mt-1">Certificates are generated automatically after verification</p>
              </div>
            ) : (
              certificates.map((cert) => (
                <div key={cert.id} className="rounded-xl border border-gray-200 bg-white p-5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <span className="text-sm font-mono text-primary-600">{cert.certificate_id}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(cert.verification_result)}`}>
                        {cert.verification_result}
                      </span>
                      <span className={`text-sm font-bold ${trustColor(cert.trust_score)}`}>
                        Trust: {cert.trust_score}
                      </span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => validateMutation.mutate(cert.certificate_id)}
                        className="px-3 py-1 text-xs bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100"
                      >
                        Validate
                      </button>
                      <a
                        href={`/api/v2/verification/certificates/${cert.certificate_id}/download`}
                        className="px-3 py-1 text-xs bg-green-50 text-green-600 rounded-lg hover:bg-green-100"
                      >
                        Download
                      </a>
                    </div>
                  </div>
                  <div className="flex items-center space-x-6 mt-3 text-xs text-gray-500">
                    <span>Request #{cert.request_id}</span>
                    <span>Algorithm: {cert.algorithm_used}</span>
                    {cert.model_before_hash && <span>Before: {cert.model_before_hash.substring(0, 12)}...</span>}
                    {cert.model_after_hash && <span>After: {cert.model_after_hash.substring(0, 12)}...</span>}
                    <span className="ml-auto">{formatDate(cert.created_at)}</span>
                  </div>
                  {cert.integrity_hash && (
                    <div className="mt-2 text-xs font-mono text-gray-400">
                      Integrity: {cert.integrity_hash.substring(0, 32)}...
                    </div>
                  )}
                  {validateMutation.data && validateMutation.data.certificate_id === cert.certificate_id && (
                    <div className={`mt-3 text-xs p-2 rounded-lg ${
                      validateMutation.data.valid ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"
                    }`}>
                      Validation: {validateMutation.data.valid ? "VALID" : "INVALID"} |
                      Hash: {validateMutation.data.hash_valid ? "OK" : "FAIL"} |
                      Signature: {validateMutation.data.signature_valid ? "OK" : "FAIL"}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {tab === "trust" && (
          <div className="space-y-6">
            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <h3 className="text-lg font-medium text-gray-700 mb-4">Trust Dashboard</h3>
              {jobs.length === 0 ? (
                <p className="text-sm text-gray-400">No verification data available</p>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="text-center p-4 rounded-lg bg-gray-50">
                    <p className="text-3xl font-bold text-gray-900">{jobs.length}</p>
                    <p className="text-xs text-gray-500 mt-1">Total Verifications</p>
                  </div>
                  <div className="text-center p-4 rounded-lg bg-green-50">
                    <p className="text-3xl font-bold text-green-600">
                      {jobs.filter((j) => j.overall_status === "passed").length}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">Passed</p>
                  </div>
                  <div className="text-center p-4 rounded-lg bg-red-50">
                    <p className="text-3xl font-bold text-red-600">
                      {jobs.filter((j) => j.overall_status === "failed").length}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">Failed</p>
                  </div>
                  <div className="text-center p-4 rounded-lg bg-primary-50">
                    <p className={`text-3xl font-bold ${trustColor(
                      jobs.reduce((sum, j) => sum + (j.trust_score || 0), 0) / Math.max(jobs.filter((j) => j.trust_score !== null).length, 1)
                    )}`}>
                      {(jobs.reduce((sum, j) => sum + (j.trust_score || 0), 0) / Math.max(jobs.filter((j) => j.trust_score !== null).length, 1)).toFixed(1)}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">Avg Trust Score</p>
                  </div>
                </div>
              )}
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <h3 className="text-sm font-medium text-gray-700 mb-4">Verification Timeline</h3>
              <div className="space-y-3">
                {jobs.slice(0, 10).map((job) => (
                  <div key={job.id} className="flex items-center space-x-4 text-sm">
                    <span className="w-2 h-2 rounded-full flex-shrink-0 bg-primary-500" />
                    <span className="text-gray-400 text-xs w-32 flex-shrink-0">{formatDate(job.created_at)}</span>
                    <span className="font-mono text-gray-600">VER-{job.id}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(job.overall_status || "pending")}`}>
                      {job.overall_status || "pending"}
                    </span>
                    {job.trust_score !== null && (
                      <span className={`font-bold ${trustColor(job.trust_score)}`}>{job.trust_score}</span>
                    )}
                    <span className="text-gray-400">Request #{job.request_id}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>
    </AuthGuard>
  );
}
