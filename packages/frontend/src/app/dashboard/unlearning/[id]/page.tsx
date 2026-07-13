"use client"

import { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import { useParams } from "next/navigation"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { clsx } from "clsx"
import * as unlearningApi from "@/lib/api/unlearning"
import type { UnlearningRequest, DeletionProof, Certificate } from "@/lib/types/unlearning"
import { formatDate } from "@/lib/utils"

const statusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-700",
  in_progress: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  retrying: "bg-orange-100 text-orange-700",
}

const stepMap: Record<string, string> = {
  pending: "Queued",
  in_progress: "Processing",
  completed: "Completed",
  failed: "Failed",
  retrying: "Retrying",
  generated: "Generated",
  verified: "Verified",
}

function StepIcon({ status }: { status: string }) {
  if (status === "completed" || status === "verified" || status === "generated") {
    return <span className="text-green-600 font-bold">✓</span>
  }
  if (status === "failed") return <span className="text-red-600 font-bold">✗</span>
  if (status === "in_progress" || status === "processing") {
    return <span className="text-blue-600 animate-pulse">◌</span>
  }
  return <span className="text-gray-400">○</span>
}

export default function UnlearningDetailPage() {
  const router = useRouter()
  const params = useParams()
  const requestId = params.id as string

  const [request, setRequest] = useState<UnlearningRequest | null>(null)
  const [proof, setProof] = useState<DeletionProof | null>(null)
  const [certificate, setCertificate] = useState<Certificate | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [verifying, setVerifying] = useState(false)
  const [verifyResult, setVerifyResult] = useState<boolean | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const req = await unlearningApi.getRequest(requestId)
      setRequest(req)

      const proofsRes = await unlearningApi.listProofs({ request_id: requestId })
      if (proofsRes.data.length > 0) {
        const p = proofsRes.data[0]
        setProof(p)
        if (p.status === "generated" || p.status === "verified") {
          try {
            const cert = await unlearningApi.getCertificate(req.proof_hash || p.proof_hash)
            setCertificate(cert)
          } catch {}
        }
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load request")
    } finally {
      setLoading(false)
    }
  }, [requestId])

  useEffect(() => { loadData() }, [loadData])

  const handleRetry = async () => {
    try {
      await unlearningApi.retryRequest(requestId)
      await loadData()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Retry failed")
    }
  }

  const handleVerify = async () => {
    if (!proof) return
    setVerifying(true)
    try {
      const result = await unlearningApi.verifyProof(proof.id)
      setVerifyResult(result.is_valid)
      await loadData()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Verification failed")
    } finally {
      setVerifying(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <p className="text-sm text-gray-500">Loading...</p>
      </div>
    )
  }

  if (error && !request) {
    return (
      <div className="space-y-6">
        <p className="text-sm text-red-600">{error}</p>
        <Button variant="outline" onClick={() => router.push("/dashboard/unlearning")}>Back</Button>
      </div>
    )
  }

  if (!request) return null

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <button onClick={() => router.push("/dashboard/unlearning")} className="text-sm text-blue-600 hover:text-blue-800 mb-1 block">
            ← Back to requests
          </button>
          <h1 className="text-2xl font-bold text-gray-900">Unlearning Request</h1>
          <p className="text-sm text-gray-500 mt-1">ID: {request.id.slice(0, 12)}...</p>
        </div>
        <div className="flex gap-2">
          {(request.status === "failed") && (
            <Button variant="secondary" onClick={handleRetry}>Retry</Button>
          )}
        </div>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {/* Status Timeline */}
      <Card>
        <CardContent className="pt-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Timeline</h3>
          <div className="space-y-3">
            {[
              { label: "Created", date: request.created_at, status: "completed" },
              { label: stepMap[request.status] || request.status, date: request.updated_at, status: request.status },
              ...(request.completed_at ? [{ label: "Completed", date: request.completed_at, status: "completed" as const }] : []),
            ].map((step, i) => (
              <div key={i} className="flex items-center gap-3">
                <StepIcon status={step.status} />
                <div>
                  <p className={clsx(
                    "text-sm font-medium",
                    step.status === "failed" ? "text-red-700" : "text-gray-900"
                  )}>
                    {step.label}
                  </p>
                  <p className="text-xs text-gray-500">{formatDate(step.date)}</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Request Details */}
      <Card>
        <CardHeader><h3 className="text-lg font-semibold">Details</h3></CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-4">
            <div>
              <dt className="text-xs text-gray-500 uppercase tracking-wider">Status</dt>
              <dd>
                <span className={clsx("text-xs px-2 py-0.5 rounded-full inline-block mt-1", statusColors[request.status])}>
                  {request.status.replace("_", " ")}
                </span>
              </dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500 uppercase tracking-wider">Priority</dt>
              <dd className="text-sm font-medium mt-1 capitalize">{request.priority}</dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500 uppercase tracking-wider">Algorithm</dt>
              <dd className="text-sm font-medium mt-1">{request.algorithm || "Pending"}</dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500 uppercase tracking-wider">Regulatory</dt>
              <dd className="text-sm font-medium mt-1 uppercase">{request.regulatory}</dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500 uppercase tracking-wider">Target Records</dt>
              <dd className="text-sm font-medium mt-1">{request.target_data_ids.length}</dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500 uppercase tracking-wider">Created</dt>
              <dd className="text-sm font-medium mt-1">{formatDate(request.created_at)}</dd>
            </div>
            {request.completed_at && (
              <div>
                <dt className="text-xs text-gray-500 uppercase tracking-wider">Completed</dt>
                <dd className="text-sm font-medium mt-1">{formatDate(request.completed_at)}</dd>
              </div>
            )}
          </dl>

          {request.error_message && (
            <div className="mt-4 p-3 bg-red-50 rounded-lg">
              <p className="text-xs text-red-600 font-medium">Error</p>
              <p className="text-sm text-red-700 mt-1">{request.error_message}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Target Data IDs */}
      <Card>
        <CardHeader><h3 className="text-lg font-semibold">Target Data IDs</h3></CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {request.target_data_ids.slice(0, 50).map((id) => (
              <span key={id} className="text-xs px-2 py-1 bg-gray-100 rounded text-gray-700 font-mono">{id}</span>
            ))}
            {request.target_data_ids.length > 50 && (
              <span className="text-xs px-2 py-1 bg-gray-100 rounded text-gray-500">
                +{request.target_data_ids.length - 50} more
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Proof & Certificate */}
      {proof && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Deletion Proof</h3>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleVerify}
                  loading={verifying}
                >
                  Verify Proof
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 gap-4">
              <div>
                <dt className="text-xs text-gray-500 uppercase tracking-wider">Status</dt>
                <dd>
                  <span className={clsx("text-xs px-2 py-0.5 rounded-full inline-block mt-1", statusColors[proof.status] || "bg-gray-100 text-gray-600")}>
                    {proof.status}
                  </span>
                </dd>
              </div>
              <div>
                <dt className="text-xs text-gray-500 uppercase tracking-wider">Algorithm</dt>
                <dd className="text-sm font-medium mt-1">{proof.algorithm}</dd>
              </div>
              <div className="col-span-2">
                <dt className="text-xs text-gray-500 uppercase tracking-wider">Merkle Root</dt>
                <dd className="text-sm font-mono mt-1 break-all">{proof.merkle_root}</dd>
              </div>
              <div className="col-span-2">
                <dt className="text-xs text-gray-500 uppercase tracking-wider">Signature</dt>
                <dd className="text-sm font-mono mt-1 break-all text-xs">{proof.signature_hex}</dd>
              </div>
            </dl>

            {verifyResult !== null && (
              <div className={clsx(
                "mt-4 p-3 rounded-lg",
                verifyResult ? "bg-green-50" : "bg-red-50"
              )}>
                <p className={clsx(
                  "text-sm font-medium",
                  verifyResult ? "text-green-700" : "text-red-700"
                )}>
                  {verifyResult ? "✓ Proof verified successfully" : "✗ Proof verification failed"}
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Certificate */}
      {certificate && (
        <Card>
          <CardHeader><h3 className="text-lg font-semibold">Deletion Certificate</h3></CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 gap-4">
              <div>
                <dt className="text-xs text-gray-500 uppercase tracking-wider">Certificate ID</dt>
                <dd className="text-sm font-mono mt-1">{certificate.certificate_id}</dd>
              </div>
              <div>
                <dt className="text-xs text-gray-500 uppercase tracking-wider">Status</dt>
                <dd>
                  <span className={clsx(
                    "text-xs px-2 py-0.5 rounded-full inline-block mt-1",
                    certificate.status === "verified" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"
                  )}>
                    {certificate.status}
                  </span>
                </dd>
              </div>
              <div>
                <dt className="text-xs text-gray-500 uppercase tracking-wider">Utility Retained</dt>
                <dd className="text-sm font-medium mt-1">{(certificate.utility_retained * 100).toFixed(1)}%</dd>
              </div>
              <div>
                <dt className="text-xs text-gray-500 uppercase tracking-wider">Processing Time</dt>
                <dd className="text-sm font-medium mt-1">{certificate.processing_time_ms}ms</dd>
              </div>
            </dl>

            {certificate.privacy_assessment && (
              <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                <p className="text-xs font-medium text-gray-700 mb-2">Privacy Assessment</p>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-gray-500">MIA Confidence:</span>{" "}
                    {(certificate.privacy_assessment.membership_inference.confidence_based.overall_accuracy * 100).toFixed(0)}%
                  </div>
                  <div>
                    <span className="text-gray-500">MIA Loss-based:</span>{" "}
                    {(certificate.privacy_assessment.membership_inference.loss_based.overall_accuracy * 100).toFixed(0)}%
                  </div>
                  {certificate.privacy_assessment.dp_estimate.epsilon !== null && (
                    <div>
                      <span className="text-gray-500">DP ε:</span>{" "}
                      {certificate.privacy_assessment.dp_estimate.epsilon}
                    </div>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {!proof && request.status === "completed" && (
        <Card>
          <CardContent className="py-6 text-center">
            <p className="text-sm text-gray-500">No proof generated for this request yet.</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
