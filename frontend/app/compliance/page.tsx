"use client";

import { useEffect, useState } from "react";
import AuthGuard from "../../components/AuthGuard";
import Navbar from "../../components/Navbar";

interface Result {
  id: number;
  request_id: number;
  model_version_before_id: number | null;
  model_version_after_id: number | null;
  algorithm: string | null;
  execution_mode: string | null;
  guarantees: string | null;
  simulated: boolean;
  privacy_score: number | null;
  estimated_cost: number | null;
  estimated_latency: number | null;
  mia_before_accuracy: number | null;
  mia_after_accuracy: number | null;
  utility_retention: number | null;
  merkle_root: string | null;
  signature: string | null;
  certificate_path: string | null;
  deletion_latency_ms: number | null;
  created_at: string;
}

interface Verification {
  verified: boolean;
  merkle_valid: boolean;
  signature_valid: boolean;
  certificate_valid: boolean;
  certificate_hash_valid: boolean;
  certificate_signature_valid: boolean;
  errors: string[];
}

const authHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem("access_token")}`,
  "Content-Type": "application/json",
});

export default function CompliancePage() {
  const [results, setResults] = useState<Result[]>([]);
  const [loading, setLoading] = useState(true);
  const [verifications, setVerifications] = useState<Record<number, Verification>>({});
  const [verifyingId, setVerifyingId] = useState<number | null>(null);

  const fetchResults = async () => {
    try {
      const requestsRes = await fetch("/api/unlearning/requests", { headers: authHeaders() });
      if (requestsRes.ok) {
        const requests = await requestsRes.json();
        const resultPromises = requests.map((r: { id: number }) =>
          fetch(`/api/unlearning/results/${r.id}`, { headers: authHeaders() }).then((res) => (res.ok ? res.json() : null))
        );
        const resolved = await Promise.all(resultPromises);
        setResults(resolved.filter(Boolean));
      }
    } catch {}
    setLoading(false);
  };

  useEffect(() => {
    fetchResults();
  }, []);

  const verifyProof = async (requestId: number) => {
    setVerifyingId(requestId);
    try {
      const res = await fetch(`/api/unlearning/results/${requestId}/verify`, { headers: authHeaders() });
      if (res.ok) {
        const payload = await res.json();
        setVerifications((prev) => ({ ...prev, [requestId]: payload }));
      }
    } catch {}
    setVerifyingId(null);
  };

  return (
    <AuthGuard>
      <Navbar />
      <main className="min-h-screen p-8 max-w-5xl mx-auto">
        <div className="space-y-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Compliance Dashboard</h1>
            <p className="text-gray-500 mt-1">Verifiable deletion certificates with cryptographic proofs</p>
          </div>

          {loading ? (
            <p className="text-gray-400">Loading...</p>
          ) : results.length === 0 ? (
            <div className="rounded-xl border border-gray-200 bg-white p-12 text-center">
              <p className="text-gray-400">No compliance certificates generated yet.</p>
              <p className="text-sm text-gray-400 mt-1">Execute an unlearning request to generate a certificate.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {results.map((result) => (
                <div key={result.id} className="rounded-xl border border-gray-200 bg-white p-6">
                  {verifications[result.request_id] && (
                    <div
                      className={`mb-4 rounded-lg border p-3 text-sm ${
                        verifications[result.request_id].verified
                          ? "border-green-200 bg-green-50 text-green-800"
                          : "border-red-200 bg-red-50 text-red-800"
                      }`}
                    >
                      <span className="font-medium">
                        {verifications[result.request_id].verified ? "Proof verified" : "Proof verification failed"}
                      </span>
                      {!verifications[result.request_id].verified && verifications[result.request_id].errors.length > 0 && (
                        <span className="ml-2">{verifications[result.request_id].errors.join(", ")}</span>
                      )}
                    </div>
                  )}

                  <div className="mb-5 flex flex-wrap items-center gap-2">
                    <span className="text-xs bg-primary-50 text-primary-700 px-2 py-0.5 rounded-full">
                      {result.algorithm ?? "unknown"}
                    </span>
                    <span className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded-full">
                      {result.guarantees ?? "unclassified"}
                    </span>
                    {result.simulated && (
                      <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full">
                        Virtual Adapter
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-3 gap-6">
                    <div>
                      <h3 className="text-sm font-medium text-gray-500 mb-3">Membership Inference Attack</h3>
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600">Before Accuracy</span>
                          <span className="font-medium">{((result.mia_before_accuracy ?? 0) * 100).toFixed(1)}%</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600">After Accuracy</span>
                          <span className="font-medium text-green-600">{((result.mia_after_accuracy ?? 0) * 100).toFixed(1)}%</span>
                        </div>
                      </div>
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-500 mb-3">Utility Metrics</h3>
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600">Retention</span>
                          <span className="font-medium">{((result.utility_retention ?? 0) * 100).toFixed(1)}%</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600">Latency</span>
                          <span className="font-medium">{result.deletion_latency_ms?.toFixed(0)} ms</span>
                        </div>
                      </div>
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-500 mb-3">Execution Profile</h3>
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600">Privacy Score</span>
                          <span className="font-medium">{((result.privacy_score ?? 0) * 100).toFixed(0)}%</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600">Est. Latency</span>
                          <span className="font-medium">{result.estimated_latency?.toFixed(2) ?? "-"} s</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600">Est. Cost</span>
                          <span className="font-medium">{result.estimated_cost?.toFixed(2) ?? "-"}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="mt-4 pt-4 border-t border-gray-100">
                    <div className="flex items-center justify-between">
                      <div className="text-xs text-gray-400 font-mono truncate max-w-md">
                        Merkle Root: {result.merkle_root?.slice(0, 32)}...
                      </div>
                      {result.certificate_path && (
                        <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                          Certificate Generated
                        </span>
                      )}
                      <div className="flex items-center gap-2">
                        <a
                          href={`/api/unlearning/results/${result.request_id}/certificate`}
                          download
                          className="text-xs bg-gray-600 text-white px-3 py-1 rounded-md hover:bg-gray-700"
                        >
                          Download
                        </a>
                        <button
                          onClick={() => verifyProof(result.request_id)}
                          disabled={verifyingId === result.request_id}
                          className="text-xs bg-primary-600 text-white px-3 py-1 rounded-md hover:bg-primary-700 disabled:opacity-50"
                        >
                          {verifyingId === result.request_id ? "Verifying..." : "Verify Proof"}
                        </button>
                      </div>
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
