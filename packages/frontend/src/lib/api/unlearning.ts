import { apiRequest } from "./client"
import type {
  UnlearningRequest, CreateUnlearningRequest,
  DeletionProof, ProofVerification, Certificate,
  PaginatedResponse,
} from "@/lib/types/unlearning"

export async function listRequests(params?: {
  page?: number
  page_size?: number
  status?: string
  model_id?: string
}): Promise<PaginatedResponse<UnlearningRequest>> {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set("page", String(params.page))
  if (params?.page_size) searchParams.set("page_size", String(params.page_size))
  if (params?.status) searchParams.set("status", params.status)
  if (params?.model_id) searchParams.set("model_id", params.model_id)
  const qs = searchParams.toString()
  return apiRequest(`/api/v1/unlearning/requests${qs ? `?${qs}` : ""}`)
}

export async function getRequest(requestId: string): Promise<UnlearningRequest> {
  return apiRequest(`/api/v1/unlearning/requests/${requestId}`)
}

export async function createRequest(data: CreateUnlearningRequest): Promise<UnlearningRequest> {
  return apiRequest("/api/v1/unlearning/requests", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function retryRequest(requestId: string): Promise<UnlearningRequest> {
  return apiRequest(`/api/v1/unlearning/requests/${requestId}/retry`, {
    method: "POST",
  })
}

export async function getQueue(params?: {
  page?: number
  page_size?: number
}): Promise<PaginatedResponse<import("@/lib/types/unlearning").DeletionQueueItem>> {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set("page", String(params.page))
  if (params?.page_size) searchParams.set("page_size", String(params.page_size))
  const qs = searchParams.toString()
  return apiRequest(`/api/v1/unlearning/queue${qs ? `?${qs}` : ""}`)
}

export async function listProofs(params?: {
  page?: number
  page_size?: number
  request_id?: string
}): Promise<PaginatedResponse<DeletionProof>> {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set("page", String(params.page))
  if (params?.page_size) searchParams.set("page_size", String(params.page_size))
  if (params?.request_id) searchParams.set("request_id", params.request_id)
  const qs = searchParams.toString()
  return apiRequest(`/api/v1/verify/proofs${qs ? `?${qs}` : ""}`)
}

export async function getProof(proofId: string): Promise<DeletionProof> {
  return apiRequest(`/api/v1/verify/proofs/${proofId}`)
}

export async function verifyProof(proofId: string): Promise<ProofVerification> {
  return apiRequest(`/api/v1/verify/proofs/${proofId}/verify`, {
    method: "POST",
  })
}

export async function getCertificate(hash: string): Promise<Certificate> {
  return apiRequest(`/api/v1/verify/certificates/${hash}`)
}
