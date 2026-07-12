"use client";

import { useEffect, useState } from "react";
import AuthGuard from "../../components/AuthGuard";
import Navbar from "../../components/Navbar";

interface UnlearningRequest {
  id: number;
  status: string;
  algorithm: string;
  reason: string | null;
  progress: number;
  created_at: string;
}

const authHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem("access_token")}`,
  "Content-Type": "application/json",
});

export default function PrivacyPage() {
  const [requests, setRequests] = useState<UnlearningRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [sampleIds, setSampleIds] = useState("");
  const [algorithm, setAlgorithm] = useState("");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [executingId, setExecutingId] = useState<number | null>(null);

  const parseIds = () =>
    sampleIds
      .split(",")
      .map((id) => Number(id.trim()))
      .filter((id) => Number.isInteger(id) && id > 0);

  const fetchRequests = async () => {
    try {
      const res = await fetch("/api/unlearning/requests", { headers: authHeaders() });
      if (res.ok) {
        setRequests(await res.json());
      }
    } catch {}
    setLoading(false);
  };

  const createRequest = async () => {
    const ids = parseIds();
    if (ids.length === 0) return;
    setSubmitting(true);
    try {
      const res = await fetch("/api/unlearning/requests", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          sample_ids: ids,
          algorithm: algorithm || null,
          reason: reason || null,
        }),
      });
      if (res.ok) {
        setSampleIds("");
        setReason("");
        setAlgorithm("");
        fetchRequests();
      }
    } catch {}
    setSubmitting(false);
  };

  const executeRequest = async (id: number) => {
    setExecutingId(id);
    try {
      const res = await fetch(`/api/unlearning/requests/${id}/execute`, {
        method: "POST",
        headers: authHeaders(),
      });
      if (res.ok) fetchRequests();
    } catch {}
    setExecutingId(null);
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  return (
    <AuthGuard>
      <Navbar />
      <main className="min-h-screen p-8 max-w-5xl mx-auto">
        <div className="space-y-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Privacy Center</h1>
            <p className="text-gray-500 mt-1">Manage data deletion and unlearning requests</p>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-3">Create Unlearning Request</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Sample IDs</label>
                <input
                  type="text"
                  value={sampleIds}
                  onChange={(e) => setSampleIds(e.target.value)}
                  placeholder="1,2,3"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Algorithm</label>
                <select
                  value={algorithm}
                  onChange={(e) => setAlgorithm(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                >
                  <option value="">auto-select</option>
                  <option value="certified_removal">certified_removal</option>
                  <option value="gradient_ascent">gradient_ascent</option>
                  <option value="influence_functions">influence_functions</option>
                  <option value="sisa">sisa</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Reason</label>
                <input
                  type="text"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Deletion request"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
            </div>
            <button
              onClick={createRequest}
              disabled={submitting || parseIds().length === 0}
              className="mt-4 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              {submitting ? "Submitting..." : "Submit Request"}
            </button>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-3">How It Works</h2>
            <div className="grid grid-cols-3 gap-4 text-sm text-gray-500">
              <div className="space-y-1">
                <p className="font-medium text-gray-700">1. Request Deletion</p>
                <p>Submit training sample IDs for removal</p>
              </div>
              <div className="space-y-1">
                <p className="font-medium text-gray-700">2. Algorithm Execution</p>
                <p>Adaptive controller selects or runs your chosen method</p>
              </div>
              <div className="space-y-1">
                <p className="font-medium text-gray-700">3. Verification</p>
                <p>MIA, utility, Merkle proof, and signature are generated</p>
              </div>
            </div>
          </div>

          {loading ? (
            <p className="text-gray-400">Loading...</p>
          ) : requests.length === 0 ? (
            <div className="rounded-xl border border-gray-200 bg-white p-12 text-center">
              <p className="text-gray-400">No deletion requests yet.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {requests.map((req) => (
                <div key={req.id} className="rounded-xl border border-gray-200 bg-white p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="font-medium text-gray-900">
                        Request #{req.id}
                        <span className="ml-2 text-xs text-gray-400">{req.algorithm}</span>
                      </p>
                      <p className="text-sm text-gray-400">{new Date(req.created_at).toLocaleString()}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      {(req.status === "pending" || req.status === "failed") && (
                        <button
                          onClick={() => executeRequest(req.id)}
                          disabled={executingId === req.id}
                          className="text-xs bg-primary-600 text-white px-3 py-1 rounded-md hover:bg-primary-700 disabled:opacity-50"
                        >
                          {executingId === req.id ? "Running..." : "Execute"}
                        </button>
                      )}
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full ${
                          req.status === "completed"
                            ? "bg-green-100 text-green-700"
                            : req.status === "processing"
                            ? "bg-blue-100 text-blue-700"
                            : req.status === "failed"
                            ? "bg-red-100 text-red-700"
                            : "bg-yellow-100 text-yellow-700"
                        }`}
                      >
                        {req.status}
                      </span>
                    </div>
                  </div>
                  {req.status === "processing" && (
                    <div className="mt-3 w-full bg-gray-100 rounded-full h-2">
                      <div
                        className="bg-primary-600 h-2 rounded-full transition-all"
                        style={{ width: `${req.progress * 100}%` }}
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </AuthGuard>
  );
}
