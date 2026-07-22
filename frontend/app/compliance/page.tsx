"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import AuthGuard from "../../components/AuthGuard";
import Navbar from "../../components/Navbar";
import { api } from "../../lib/api";

interface DashboardData {
  governance_score: number;
  total_policies: number;
  active_policies: number;
  total_consents: number;
  active_consents: number;
  pending_approvals: number;
  total_violations: number;
  recent_notifications: { id: number; message: string; severity: string; created_at: string }[];
}

interface Policy {
  id: number;
  name: string;
  description: string;
  policy_type: string;
  regulation: string;
  status: string;
  created_at: string;
}

interface Consent {
  id: number;
  subject: string;
  purpose: string;
  regulation: string;
  status: string;
  dataset_id: number | null;
  granted_at: string;
  expires_at: string | null;
}

interface Approval {
  id: number;
  title: string;
  description: string;
  type: string;
  status: string;
  requester: string;
  created_at: string;
}

interface Workflow {
  id: number;
  name: string;
  status: string;
  regulation: string;
  created_at: string;
}

interface Report {
  id: number;
  title: string;
  regulation: string;
  status: string;
  created_at: string;
}

function statusColor(s: string): string {
  switch (s) {
    case "active":
    case "granted":
    case "completed":
    case "passed":
    case "approved":
      return "bg-green-100 text-green-700";
    case "pending":
    case "in_progress":
      return "bg-yellow-100 text-yellow-700";
    case "withdrawn":
    case "expired":
    case "failed":
    case "rejected":
    case "inactive":
      return "bg-red-100 text-red-700";
    case "running":
      return "bg-blue-100 text-blue-700";
    default:
      return "bg-gray-100 text-gray-500";
  }
}

function scoreColor(score: number): string {
  if (score > 80) return "text-green-600";
  if (score > 60) return "text-yellow-600";
  return "text-red-600";
}

function scoreBg(score: number): string {
  if (score > 80) return "bg-green-50 border-green-200";
  if (score > 60) return "bg-yellow-50 border-yellow-200";
  return "bg-red-50 border-red-200";
}

function severityColor(s: string): string {
  switch (s) {
    case "high":
    case "critical":
      return "bg-red-100 text-red-700";
    case "medium":
    case "warning":
      return "bg-yellow-100 text-yellow-700";
    case "low":
    case "info":
      return "bg-blue-100 text-blue-700";
    default:
      return "bg-gray-100 text-gray-500";
  }
}

function formatDate(d: string | null): string {
  if (!d) return "-";
  return new Date(d).toLocaleString();
}

type Tab = "dashboard" | "policies" | "consent" | "approvals" | "workflows";

export default function CompliancePage() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<Tab>("dashboard");

  const [policyForm, setPolicyForm] = useState({ name: "", description: "", policy_type: "data_retention", regulation: "GDPR" });
  const [showPolicyModal, setShowPolicyModal] = useState(false);

  const [consentForm, setConsentForm] = useState({ subject: "", purpose: "", dataset_id: "", regulation: "GDPR", expires_days: "" });
  const [showConsentModal, setShowConsentModal] = useState(false);

  const { data: dashData, isLoading: loadingDash } = useQuery({
    queryKey: ["governanceDashboard"],
    queryFn: () => api.governance.dashboard(),
  });

  const { data: policiesData, isLoading: loadingPolicies } = useQuery({
    queryKey: ["governancePolicies"],
    queryFn: () => api.governance.policies(),
  });

  const { data: consentsData, isLoading: loadingConsents } = useQuery({
    queryKey: ["governanceConsents"],
    queryFn: () => api.governance.consents(),
  });

  const { data: approvalsData, isLoading: loadingApprovals } = useQuery({
    queryKey: ["governanceApprovals"],
    queryFn: () => api.governance.pendingApprovals(),
  });

  const { data: workflowsData, isLoading: loadingWorkflows } = useQuery({
    queryKey: ["governanceWorkflows"],
    queryFn: () => api.governance.workflows(),
  });

  const { data: reportsData, isLoading: loadingReports } = useQuery({
    queryKey: ["governanceReports"],
    queryFn: () => api.governance.reports(),
  });

  const createPolicyMutation = useMutation({
    mutationFn: (data: { name: string; description: string; policy_type: string; regulation: string }) =>
      api.governance.createPolicy(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["governancePolicies"] });
      queryClient.invalidateQueries({ queryKey: ["governanceDashboard"] });
      setShowPolicyModal(false);
      setPolicyForm({ name: "", description: "", policy_type: "data_retention", regulation: "GDPR" });
    },
  });

  const grantConsentMutation = useMutation({
    mutationFn: (data: { subject: string; purpose: string; dataset_id: number; regulation: string; expires_days?: number }) =>
      api.governance.grantConsent(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["governanceConsents"] });
      queryClient.invalidateQueries({ queryKey: ["governanceDashboard"] });
      setShowConsentModal(false);
      setConsentForm({ subject: "", purpose: "", dataset_id: "", regulation: "GDPR", expires_days: "" });
    },
  });

  const approveMutation = useMutation({
    mutationFn: (id: number) => api.governance.approveApproval(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["governanceApprovals"] });
      queryClient.invalidateQueries({ queryKey: ["governanceDashboard"] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (id: number) => api.governance.rejectApproval(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["governanceApprovals"] });
      queryClient.invalidateQueries({ queryKey: ["governanceDashboard"] });
    },
  });

  const dashboard: DashboardData | undefined = dashData;
  const policies: Policy[] = policiesData?.policies || [];
  const consents: Consent[] = consentsData?.consents || [];
  const approvals: Approval[] = approvalsData?.approvals || [];
  const workflows: Workflow[] = workflowsData?.workflows || [];
  const reports: Report[] = reportsData?.reports || [];

  const tabs: { key: Tab; label: string }[] = [
    { key: "dashboard", label: "Dashboard" },
    { key: "policies", label: "Policies" },
    { key: "consent", label: "Consent" },
    { key: "approvals", label: "Approvals" },
    { key: "workflows", label: "Workflows & Reports" },
  ];

  return (
    <AuthGuard>
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 pt-20">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Compliance &amp; Governance</h1>
            <p className="text-sm text-gray-500 mt-1">Policies, consent management, approvals, and regulatory compliance</p>
          </div>
        </div>

        {dashboard && (
          <div className={`rounded-xl border p-5 mb-6 ${scoreBg(dashboard.governance_score)}`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">Governance Score</p>
                <p className={`text-4xl font-bold mt-1 ${scoreColor(dashboard.governance_score)}`}>
                  {dashboard.governance_score}
                  <span className="text-lg font-normal text-gray-400 ml-1">/ 100</span>
                </p>
              </div>
              <div className="grid grid-cols-4 gap-4 text-center">
                {[
                  { label: "Total Policies", value: dashboard.total_policies, color: "text-gray-900" },
                  { label: "Active Consents", value: dashboard.active_consents, color: "text-green-600" },
                  { label: "Pending Approvals", value: dashboard.pending_approvals, color: "text-yellow-600" },
                  { label: "Violations", value: dashboard.total_violations, color: "text-red-600" },
                ].map((s) => (
                  <div key={s.label} className="px-4">
                    <p className={`text-xl font-bold ${s.color}`}>{s.value}</p>
                    <p className="text-xs text-gray-500">{s.label}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        <div className="flex space-x-1 bg-gray-100 rounded-lg p-1 mb-6 w-fit">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-4 py-2 text-sm rounded-md transition-colors ${
                tab === t.key ? "bg-white shadow-sm text-gray-900 font-medium" : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === "dashboard" && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: "Total Policies", value: dashboard?.total_policies ?? 0, color: "text-gray-900" },
                { label: "Active Policies", value: dashboard?.active_policies ?? 0, color: "text-blue-600" },
                { label: "Total Consents", value: dashboard?.total_consents ?? 0, color: "text-gray-900" },
                { label: "Active Consents", value: dashboard?.active_consents ?? 0, color: "text-green-600" },
                { label: "Pending Approvals", value: dashboard?.pending_approvals ?? 0, color: "text-yellow-600" },
                { label: "Total Violations", value: dashboard?.total_violations ?? 0, color: "text-red-600" },
              ].map((s) => (
                <div key={s.label} className="rounded-xl border border-gray-200 bg-white p-4">
                  <p className="text-xs text-gray-500">{s.label}</p>
                  <p className={`text-xl font-bold mt-1 ${s.color}`}>{s.value}</p>
                </div>
              ))}
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-5">
              <h3 className="text-sm font-medium text-gray-700 mb-3">Recent Notifications</h3>
              {!dashboard?.recent_notifications?.length ? (
                <p className="text-sm text-gray-400">No recent notifications</p>
              ) : (
                <div className="space-y-2">
                  {dashboard.recent_notifications.map((n) => (
                    <div key={n.id} className="flex items-center justify-between text-sm py-2 border-b border-gray-100 last:border-0">
                      <div className="flex items-center space-x-3">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${severityColor(n.severity)}`}>{n.severity}</span>
                        <span className="text-gray-700">{n.message}</span>
                      </div>
                      <span className="text-xs text-gray-400">{formatDate(n.created_at)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {tab === "policies" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-medium text-gray-900">Policies</h2>
              <button
                onClick={() => setShowPolicyModal(true)}
                className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors"
              >
                Create Policy
              </button>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Regulation</th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {loadingPolicies ? (
                    [1, 2, 3].map((i) => (
                      <tr key={i}>
                        <td colSpan={5} className="px-5 py-4"><div className="h-4 bg-gray-200 rounded animate-pulse w-1/3" /></td>
                      </tr>
                    ))
                  ) : policies.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-5 py-12 text-center text-sm text-gray-400">No policies created yet</td>
                    </tr>
                  ) : (
                    policies.map((p) => (
                      <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-5 py-3">
                          <p className="text-sm font-medium text-gray-900">{p.name}</p>
                          <p className="text-xs text-gray-400 truncate max-w-xs">{p.description}</p>
                        </td>
                        <td className="px-5 py-3 text-sm text-gray-600">{p.policy_type.replace(/_/g, " ")}</td>
                        <td className="px-5 py-3">
                          <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">{p.regulation}</span>
                        </td>
                        <td className="px-5 py-3">
                          <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(p.status)}`}>{p.status}</span>
                        </td>
                        <td className="px-5 py-3 text-xs text-gray-400">{formatDate(p.created_at)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {showPolicyModal && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
                <div className="bg-white rounded-xl border border-gray-200 shadow-xl w-full max-w-md p-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Create Policy</h3>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">Name</label>
                      <input
                        type="text"
                        value={policyForm.name}
                        onChange={(e) => setPolicyForm({ ...policyForm, name: e.target.value })}
                        className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                        placeholder="Policy name"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">Description</label>
                      <textarea
                        value={policyForm.description}
                        onChange={(e) => setPolicyForm({ ...policyForm, description: e.target.value })}
                        className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                        rows={3}
                        placeholder="Policy description"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">Policy Type</label>
                      <select
                        value={policyForm.policy_type}
                        onChange={(e) => setPolicyForm({ ...policyForm, policy_type: e.target.value })}
                        className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                      >
                        <option value="data_retention">Data Retention</option>
                        <option value="consent_required">Consent Required</option>
                        <option value="deletion_required">Deletion Required</option>
                        <option value="access_control">Access Control</option>
                        <option value="audit_required">Audit Required</option>
                        <option value="data_minimization">Data Minimization</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">Regulation</label>
                      <select
                        value={policyForm.regulation}
                        onChange={(e) => setPolicyForm({ ...policyForm, regulation: e.target.value })}
                        className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                      >
                        <option value="GDPR">GDPR</option>
                        <option value="CCPA">CCPA</option>
                        <option value="DPDP">DPDP</option>
                        <option value="HIPAA">HIPAA</option>
                      </select>
                    </div>
                  </div>
                  <div className="flex justify-end space-x-2 mt-6">
                    <button
                      onClick={() => setShowPolicyModal(false)}
                      className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => createPolicyMutation.mutate(policyForm)}
                      disabled={!policyForm.name || createPolicyMutation.isPending}
                      className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {createPolicyMutation.isPending ? "Creating..." : "Create"}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {tab === "consent" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-medium text-gray-900">Consent Management</h2>
              <button
                onClick={() => setShowConsentModal(true)}
                className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors"
              >
                Grant Consent
              </button>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Subject</th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Purpose</th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Regulation</th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Granted</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {loadingConsents ? (
                    [1, 2, 3].map((i) => (
                      <tr key={i}>
                        <td colSpan={5} className="px-5 py-4"><div className="h-4 bg-gray-200 rounded animate-pulse w-1/3" /></td>
                      </tr>
                    ))
                  ) : consents.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-5 py-12 text-center text-sm text-gray-400">No consent records yet</td>
                    </tr>
                  ) : (
                    consents.map((c) => (
                      <tr key={c.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-5 py-3 text-sm font-medium text-gray-900">{c.subject}</td>
                        <td className="px-5 py-3 text-sm text-gray-600">{c.purpose}</td>
                        <td className="px-5 py-3">
                          <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">{c.regulation}</span>
                        </td>
                        <td className="px-5 py-3">
                          <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(c.status)}`}>{c.status}</span>
                        </td>
                        <td className="px-5 py-3 text-xs text-gray-400">{formatDate(c.granted_at)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {showConsentModal && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
                <div className="bg-white rounded-xl border border-gray-200 shadow-xl w-full max-w-md p-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Grant Consent</h3>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">Subject</label>
                      <input
                        type="text"
                        value={consentForm.subject}
                        onChange={(e) => setConsentForm({ ...consentForm, subject: e.target.value })}
                        className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                        placeholder="e.g. user@example.com or user_id:123"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">Purpose</label>
                      <input
                        type="text"
                        value={consentForm.purpose}
                        onChange={(e) => setConsentForm({ ...consentForm, purpose: e.target.value })}
                        className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                        placeholder="e.g. model training, analytics"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">Dataset ID</label>
                      <input
                        type="number"
                        value={consentForm.dataset_id}
                        onChange={(e) => setConsentForm({ ...consentForm, dataset_id: e.target.value })}
                        className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                        placeholder="Dataset ID"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">Regulation</label>
                      <select
                        value={consentForm.regulation}
                        onChange={(e) => setConsentForm({ ...consentForm, regulation: e.target.value })}
                        className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                      >
                        <option value="GDPR">GDPR</option>
                        <option value="CCPA">CCPA</option>
                        <option value="DPDP">DPDP</option>
                        <option value="HIPAA">HIPAA</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">Expires in Days (optional)</label>
                      <input
                        type="number"
                        value={consentForm.expires_days}
                        onChange={(e) => setConsentForm({ ...consentForm, expires_days: e.target.value })}
                        className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                        placeholder="e.g. 365"
                      />
                    </div>
                  </div>
                  <div className="flex justify-end space-x-2 mt-6">
                    <button
                      onClick={() => setShowConsentModal(false)}
                      className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => {
                        grantConsentMutation.mutate({
                          subject: consentForm.subject,
                          purpose: consentForm.purpose,
                          dataset_id: Number(consentForm.dataset_id),
                          regulation: consentForm.regulation,
                          ...(consentForm.expires_days ? { expires_days: Number(consentForm.expires_days) } : {}),
                        });
                      }}
                      disabled={!consentForm.subject || !consentForm.purpose || grantConsentMutation.isPending}
                      className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {grantConsentMutation.isPending ? "Granting..." : "Grant"}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {tab === "approvals" && (
          <div className="space-y-4">
            <h2 className="text-lg font-medium text-gray-900">Pending Approvals</h2>

            {loadingApprovals ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="rounded-xl border border-gray-200 bg-white p-5 animate-pulse">
                    <div className="h-4 bg-gray-200 rounded w-1/2 mb-3" />
                    <div className="h-3 bg-gray-200 rounded w-2/3" />
                  </div>
                ))}
              </div>
            ) : approvals.length === 0 ? (
              <div className="rounded-xl border border-gray-200 bg-white p-12 text-center">
                <p className="text-gray-500 text-lg font-medium">No pending approvals</p>
                <p className="text-gray-400 text-sm mt-1">All approval requests have been processed</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {approvals.map((a) => (
                  <div key={a.id} className="rounded-xl border border-gray-200 bg-white p-5">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="text-sm font-medium text-gray-900">{a.title}</h3>
                        <p className="text-xs text-gray-500 mt-1">{a.description}</p>
                      </div>
                      <span className={`text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${statusColor(a.status)}`}>{a.status}</span>
                    </div>
                    <div className="flex items-center space-x-4 text-xs text-gray-500 mb-4">
                      <span>Type: {a.type}</span>
                      <span>Requester: {a.requester}</span>
                      <span>{formatDate(a.created_at)}</span>
                    </div>
                    {a.status === "pending" && (
                      <div className="flex space-x-2">
                        <button
                          onClick={() => approveMutation.mutate(a.id)}
                          disabled={approveMutation.isPending}
                          className="px-3 py-1.5 text-xs font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                        >
                          {approveMutation.isPending ? "Approving..." : "Approve"}
                        </button>
                        <button
                          onClick={() => rejectMutation.mutate(a.id)}
                          disabled={rejectMutation.isPending}
                          className="px-3 py-1.5 text-xs font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
                        >
                          {rejectMutation.isPending ? "Rejecting..." : "Reject"}
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === "workflows" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-3">
              <h2 className="text-lg font-medium text-gray-900">Workflows</h2>
              <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                      <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Regulation</th>
                      <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {loadingWorkflows ? (
                      [1, 2, 3].map((i) => (
                        <tr key={i}>
                          <td colSpan={3} className="px-5 py-4"><div className="h-4 bg-gray-200 rounded animate-pulse w-1/3" /></td>
                        </tr>
                      ))
                    ) : workflows.length === 0 ? (
                      <tr>
                        <td colSpan={3} className="px-5 py-12 text-center text-sm text-gray-400">No workflows found</td>
                      </tr>
                    ) : (
                      workflows.map((w) => (
                        <tr key={w.id} className="hover:bg-gray-50 transition-colors">
                          <td className="px-5 py-3">
                            <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(w.status)}`}>{w.status}</span>
                          </td>
                          <td className="px-5 py-3">
                            <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">{w.regulation}</span>
                          </td>
                          <td className="px-5 py-3 text-xs text-gray-400">{formatDate(w.created_at)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="space-y-3">
              <h2 className="text-lg font-medium text-gray-900">Reports</h2>
              <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Regulation</th>
                      <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                      <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {loadingReports ? (
                      [1, 2, 3].map((i) => (
                        <tr key={i}>
                          <td colSpan={3} className="px-5 py-4"><div className="h-4 bg-gray-200 rounded animate-pulse w-1/3" /></td>
                        </tr>
                      ))
                    ) : reports.length === 0 ? (
                      <tr>
                        <td colSpan={3} className="px-5 py-12 text-center text-sm text-gray-400">No reports found</td>
                      </tr>
                    ) : (
                      reports.map((r) => (
                        <tr key={r.id} className="hover:bg-gray-50 transition-colors">
                          <td className="px-5 py-3">
                            <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">{r.regulation}</span>
                          </td>
                          <td className="px-5 py-3">
                            <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(r.status)}`}>{r.status}</span>
                          </td>
                          <td className="px-5 py-3 text-xs text-gray-400">{formatDate(r.created_at)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </main>
    </AuthGuard>
  );
}
