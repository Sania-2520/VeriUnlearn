export interface UnlearningRequest {
  id: string
  tenant_id: string
  model_id: string
  model_version_id: string
  target_data_ids: string[]
  status: "pending" | "in_progress" | "completed" | "failed" | "retrying"
  priority: "low" | "medium" | "high" | "critical"
  algorithm: string | null
  regulatory: string
  proof_hash: string | null
  metadata: Record<string, unknown>
  error_message: string | null
  created_by: string
  created_at: string
  updated_at: string
  completed_at: string | null
}

export interface CreateUnlearningRequest {
  model_id: string
  model_version_id?: string
  target_data_ids: string[]
  priority?: "low" | "medium" | "high" | "critical"
  regulatory?: string
  metadata?: Record<string, unknown>
}

export interface UnlearningJob {
  id: string
  request_id: string
  job_type: string
  status: "queued" | "running" | "completed" | "failed"
  progress: number
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface DeletionQueueItem {
  id: string
  request_id: string
  data_id: string
  status: "pending" | "processing" | "completed" | "failed"
  shard_index: number | null
  created_at: string
  completed_at: string | null
}

export interface ModelVersion {
  id: string
  model_name: string
  version: string
  algorithm: string
  status: "active" | "archived" | "training"
  config: Record<string, unknown>
  created_at: string
}

export interface DeletionProof {
  id: string
  request_id: string
  proof_hash: string
  merkle_root: string
  signature_hex: string
  public_key_pem: string
  leaf_count: number
  algorithm: string
  status: "pending" | "generated" | "verified" | "failed"
  created_at: string
  verified_at: string | null
  verified_by: string | null
}

export interface ProofVerification {
  id: string
  proof_id: string
  is_valid: boolean
  verified_by: string
  verified_at: string
  algorithm: string
}

export interface Certificate {
  certificate_id: string
  version: string
  algorithm: string
  target_data_ids: string[]
  unlearning_result: boolean
  utility_retained: number
  processing_time_ms: number
  merkle_proof: {
    root: string
    signature_hex: string
    public_key_pem: string
    leaf_count: number
  }
  privacy_assessment: {
    membership_inference: {
      confidence_based: { overall_accuracy: number; f1_score: number }
      loss_based: { overall_accuracy: number; f1_score: number }
    }
    dp_estimate: { epsilon: number | null; delta: number | null }
  }
  regulatory: string
  status: string
}

export interface PaginatedResponse<T> {
  data: T[]
  meta: {
    page: number
    page_size: number
    total: number
    total_pages: number
  }
}
