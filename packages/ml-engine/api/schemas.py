"""Pydantic request models for the VeriUnlearn ML Engine API.

Every model was moved verbatim from the historical ``api.py`` monolith so that
the public HTTP contract is byte-for-byte identical.
"""

from typing import Any, Optional

from pydantic import BaseModel


class UnlearningRequest(BaseModel):
    target_data_ids: list[str]
    model_type: str = "transformer"
    model_name: str = ""
    data_size: int = 0
    latency_ms: int = 500
    accuracy_target: float = 0.95
    regulatory: str = "gdpr"
    config: dict = {}


class ProofRequest(BaseModel):
    deletion_steps: list[str]
    algorithm: str = "ed25519"


class VerificationRequest(BaseModel):
    message: str
    signature_hex: str
    public_key_pem: str


class CertificateRequest(BaseModel):
    target_data_ids: list[str]
    model_name: str = ""
    data_size: int = 0
    regulatory: str = "gdpr"
    config: dict = {}


class ZKProofRequest(BaseModel):
    leaf_data: str
    all_leaves: list[str]
    hash_algorithm: str = "sha3_256"


class ZKVerifyRequest(BaseModel):
    proof: dict[str, Any]


class MIARequest(BaseModel):
    model_name: str = ""
    data_size: int = 0
    target_data_ids: list[str] = []
    config: dict = {}


class LoRATrainRequest(BaseModel):
    conversations: list[dict] = []
    model_name: str = "qwen2.5-0.5b"
    lora_r: int = 16
    lora_alpha: int = 32
    num_epochs: int = 3
    batch_size: int = 4
    learning_rate: float = 2e-4
    remove_data_ids: list[str] = []


class InferenceRequestModel(BaseModel):
    prompt: str
    max_new_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    stream: bool = False
    adapter_name: Optional[str] = None
    system_prompt: Optional[str] = None


class RAGUploadRequest(BaseModel):
    text: str
    source_name: str = "document"
    metadata: dict = {}


class RAGSearchRequest(BaseModel):
    query: str
    top_k: int = 5
    filters: dict = {}


class RAGProcessRequest(BaseModel):
    """Request model for asynchronous document processing (Celery path)."""

    document_id: str
    filename: str = "document"
    file_type: str = "txt"
    storage_path: str = ""
    text: str = ""
    metadata: dict = {}


class RAGEmbeddingsRequest(BaseModel):
    """Request model for (re)generating embeddings for an indexed document."""

    document_id: str
    chunk_count: int = 0


class RAGOCRRequest(BaseModel):
    """Request model for OCR-based document extraction (Celery path)."""

    document_id: str
    storage_path: str = ""
    file_type: str = "pdf"
    metadata: dict = {}


class RAGVectorUpsertRequest(BaseModel):
    """Upsert a raw vector (memory / non-document collections)."""

    collection: str = "documents"
    point_id: str
    vector: list[float]
    payload: dict = {}


class RAGVectorDeleteRequest(BaseModel):
    """Delete vectors from a collection by an exact-match payload filter."""

    collection: str = "documents"
    filter: dict = {}


class ConversationRecordRequest(BaseModel):
    user_id: str
    tenant_id: str
    turns: list[dict]
    feedback: Optional[dict] = None


class E2EDeletionRequest(BaseModel):
    tenant_id: str = "default"
    user_id: str = "system"
    target_data_ids: list[str]
    model_name: str = "default"
    reason: str = "User deletion request"
    regulatory: str = "gdpr"
    priority: str = "medium"


class ModelRegistryRequest(BaseModel):
    model_name: str
    checkpoint_path: str
    algorithm: str = "hybrid"
    parent_version_id: Optional[str] = None
    config: dict = {}
    metrics: dict = {}


class AdapterLoadRequest(BaseModel):
    adapter_name: str
    adapter_path: str


class AdapterSwapRequest(BaseModel):
    old_adapter: Optional[str] = None
    new_adapter: str
    adapter_path: str


class ExplainSamplesRequest(BaseModel):
    samples: list[list[float]]
    feature_names: Optional[list[str]] = None
    method: str = "shap"
    model_type: str = "default"


class ExplainFeaturesRequest(BaseModel):
    dataset: list[list[float]]
    feature_names: Optional[list[str]] = None
    method: str = "shap"


class ExplainCompareRequest(BaseModel):
    pre_unlearn_samples: list[list[float]]
    post_unlearn_samples: list[list[float]]
    feature_names: Optional[list[str]] = None
    method: str = "shap"


class PrivacyHeatmapRequest(BaseModel):
    samples: list[list[float]]
    privacy_scores: list[float]
    feature_names: Optional[list[str]] = None


class DriftRequest(BaseModel):
    pre_confidences: list[float]
    post_confidences: list[float]
    pre_importances: list[dict[str, float]]
    post_importances: list[dict[str, float]]


class RegisterAdapterRequest(BaseModel):
    adapter_name: str
    adapter_path: str
    base_model_name: str = ""
    config: dict = {}
    tags: dict = {}


class AdapterVersionActionRequest(BaseModel):
    adapter_name: str
    version_id: str


class CanarySetupRequest(BaseModel):
    adapter_name: str
    stable_version_id: str
    canary_version_id: str
    canary_traffic_pct: Optional[float] = None


class RecordMetricsRequest(BaseModel):
    adapter_name: str
    version_id: str
    latency_ms: float = 0.0
    success: bool = True


class InversionAttackRequest(BaseModel):
    target_classes: list[int]
    num_samples: int = 1
    input_dim: int = 20
    iterations: int = 500
    learning_rate: float = 0.1


class ShadowMIARequest(BaseModel):
    num_shadow_models: int = 5
    shadow_data_size: int = 200
    shadow_epochs: int = 50


class ExtractionAttackRequest(BaseModel):
    input_dim: int = 20
    num_classes: int = 2
    num_queries: int = 1000
    extraction_epochs: int = 200


class HPORequest(BaseModel):
    n_trials: int = 10
    direction: str = "maximize"
    param_space: dict = {}
    study_name: Optional[str] = None


class ModelExportRequest(BaseModel):
    format: str = "onnx"
    model_name: str = "model"
    input_dim: int = 20
    num_classes: int = 2
    fp16: bool = False


__all__ = [
    "AdapterLoadRequest",
    "AdapterSwapRequest",
    "AdapterVersionActionRequest",
    "CanarySetupRequest",
    "CertificateRequest",
    "ConversationRecordRequest",
    "DriftRequest",
    "E2EDeletionRequest",
    "ExplainCompareRequest",
    "ExplainFeaturesRequest",
    "ExplainSamplesRequest",
    "ExtractionAttackRequest",
    "HPORequest",
    "InferenceRequestModel",
    "InversionAttackRequest",
    "LoRATrainRequest",
    "MIARequest",
    "ModelExportRequest",
    "ModelRegistryRequest",
    "PrivacyHeatmapRequest",
    "ProofRequest",
    "RAGEmbeddingsRequest",
    "RAGOCRRequest",
    "RAGProcessRequest",
    "RAGSearchRequest",
    "RAGUploadRequest",
    "RAGVectorDeleteRequest",
    "RAGVectorUpsertRequest",
    "RecordMetricsRequest",
    "RegisterAdapterRequest",
    "ShadowMIARequest",
    "UnlearningRequest",
    "VerificationRequest",
    "ZKProofRequest",
    "ZKVerifyRequest",
]
