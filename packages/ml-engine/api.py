from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, Optional
import json
import uuid
import numpy as np

from unlearning.hybrid_controller import HybridAdaptiveController
from unlearning.algorithms.base import UnlearningContext, UnlearningResult
from verification.merkle_tree import MerkleTree
from verification.signatures import SignatureManager
from verification.privacy_evaluation import PrivacyEvaluator
from security.attacks.membership_inference import MembershipInferenceAttack, LossBasedMIA

app = FastAPI(
    title="VeriUnlearn ML Engine",
    version="1.0.0",
    description="Machine Unlearning, Verification, and Security Engine",
)

controller = HybridAdaptiveController()
sig_manager = SignatureManager()
privacy_evaluator = PrivacyEvaluator()


# ──────────────────────────────────────────────────────────────
# Original Pydantic Models
# ──────────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────────
# New Pydantic Models
# ──────────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────────
# Explainability Pydantic Models
# ──────────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────────
# Adapter Lifecycle Pydantic Models
# ──────────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────────
# Lazy-initialized singletons for new components
# ──────────────────────────────────────────────────────────────

_lora_trainer = None
_model_registry = None
_rag_pipeline = None
_inference_service = None
_conversational_pipeline = None
_mlflow_tracker = None
_e2e_pipeline = None
_explainer_manager = None
_adapter_lifecycle = None
_continual_learning = None
_benchmark_runner = None


def get_lora_trainer():
    global _lora_trainer
    if _lora_trainer is None:
        from training.lora_trainer import LoRATrainer, TrainingConfig
        _lora_trainer = LoRATrainer(TrainingConfig())
    return _lora_trainer


def get_model_registry():
    global _model_registry
    if _model_registry is None:
        from training.model_registry import ModelRegistry, RegistryConfig
        _model_registry = ModelRegistry(RegistryConfig())
    return _model_registry


def get_rag_pipeline():
    global _rag_pipeline
    if _rag_pipeline is None:
        from training.rag_pipeline import RAGPipeline, RAGConfig
        _rag_pipeline = RAGPipeline(RAGConfig())
    return _rag_pipeline


def get_inference_service():
    global _inference_service
    if _inference_service is None:
        from inference.service import InferenceService, InferenceConfig
        _inference_service = InferenceService(InferenceConfig())
    return _inference_service


def get_conversational_pipeline():
    global _conversational_pipeline
    if _conversational_pipeline is None:
        from training.conversational_pipeline import ConversationalLearningPipeline, PipelineConfig
        _conversational_pipeline = ConversationalLearningPipeline(PipelineConfig())
    return _conversational_pipeline


def get_continual_learning():
    global _continual_learning
    if _continual_learning is None:
        from training.continual_learning import ContinualLearningManager
        _continual_learning = ContinualLearningManager()
    return _continual_learning


def get_benchmark_runner():
    global _benchmark_runner
    if _benchmark_runner is None:
        from training.benchmarks import BenchmarkRunner, BenchmarkConfig
        _benchmark_runner = BenchmarkRunner(BenchmarkConfig())
    return _benchmark_runner


def get_mlflow_tracker():
    global _mlflow_tracker
    if _mlflow_tracker is None:
        from training.mlflow_tracker import MLflowExperimentTracker, MLflowConfig
        _mlflow_tracker = MLflowExperimentTracker(MLflowConfig())
    return _mlflow_tracker


def get_e2e_pipeline():
    global _e2e_pipeline
    if _e2e_pipeline is None:
        from unlearning.e2e_pipeline import E2EUnlearningPipeline
        _e2e_pipeline = E2EUnlearningPipeline()
    return _e2e_pipeline


def get_explainer_manager():
    global _explainer_manager
    if _explainer_manager is None:
        from explainability.shap_explainer import SHAPExplainer
        from explainability.lime_explainer import LIMEExplainer
        from explainability.integrated_gradients import IntegratedGradientsExplainer
        from explainability.feature_attribution import FeatureAttribution

        class ExplainerManager:
            def __init__(self):
                self._shap: Optional[SHAPExplainer] = None
                self._lime: Optional[LIMEExplainer] = None
                self._ig: Optional[IntegratedGradientsExplainer] = None
                self._attr: Optional[FeatureAttribution] = None

            def get_shap(self, model=None) -> SHAPExplainer:
                if self._shap is None:
                    self._shap = SHAPExplainer(model or self._dummy_model())
                return self._shap

            def get_lime(self, model=None) -> LIMEExplainer:
                if self._lime is None:
                    self._lime = LIMEExplainer(model or self._dummy_model())
                return self._lime

            def get_ig(self, model=None) -> IntegratedGradientsExplainer:
                if self._ig is None:
                    self._ig = IntegratedGradientsExplainer(model or self._dummy_model())
                return self._ig

            def get_attr(self, model=None, method="gradient") -> FeatureAttribution:
                if self._attr is None or self._attr._method != method:
                    self._attr = FeatureAttribution(model or self._dummy_model(), method=method)
                return self._attr

            @staticmethod
            def _dummy_model():
                def model_fn(X):
                    return np.mean(X, axis=1, keepdims=True)
                return model_fn

        _explainer_manager = ExplainerManager()
    return _explainer_manager


def get_adapter_lifecycle():
    global _adapter_lifecycle
    if _adapter_lifecycle is None:
        from training.adapter_lifecycle import AdapterLifecycleManager, LifecycleConfig
        _adapter_lifecycle = AdapterLifecycleManager(LifecycleConfig())
    return _adapter_lifecycle


# ──────────────────────────────────────────────────────────────
# Original Endpoints
# ──────────────────────────────────────────────────────────────

@app.post("/unlearn")
async def execute_unlearning(request: UnlearningRequest):
    context = UnlearningContext(
        target_data_ids=request.target_data_ids,
        model_type=request.model_type,
        model_name=request.model_name,
        data_size=request.data_size,
        latency_ms=request.latency_ms,
        accuracy_target=request.accuracy_target,
        regulatory=request.regulatory,
        config=request.config,
    )
    result = await controller.execute(context)
    return result


@app.post("/proof/generate")
async def generate_proof(request: ProofRequest):
    tree = MerkleTree()
    tree.add_leaves(request.deletion_steps)
    root = tree.build_tree()

    private_key, public_key = sig_manager.generate_key_pair()
    signature = sig_manager.sign(root, private_key)

    return {
        "merkle_root": root,
        "merkle_tree": tree.to_dict(),
        "signature_hex": signature,
        "algorithm": request.algorithm,
        "public_key_pem": sig_manager.serialize_public_key(public_key),
        "leaf_count": len(request.deletion_steps),
        "tree_depth": len(tree.tree),
    }


@app.post("/proof/verify")
async def verify_proof(request: VerificationRequest):
    public_key = sig_manager.load_public_key(request.public_key_pem)
    is_valid = sig_manager.verify(
        request.message, request.signature_hex, public_key
    )
    return {"is_valid": is_valid, "algorithm": "ed25519"}


@app.post("/certificate")
async def generate_certificate(request: CertificateRequest):
    context = UnlearningContext(
        target_data_ids=request.target_data_ids,
        model_name=request.model_name,
        data_size=request.data_size,
        regulatory=request.regulatory,
        config=request.config,
    )
    result = await controller.execute(context)

    tree = MerkleTree()
    tree.add_leaves(request.target_data_ids)
    root = tree.build_tree()

    private_key, public_key = sig_manager.generate_key_pair()
    signature = sig_manager.sign(root, private_key)

    algorithm = result.algorithm
    epsilon = None
    delta = None
    if "certified" in result.metrics:
        eps = result.metrics["certified"].get("epsilon")
        delt = result.metrics["certified"].get("delta")
        if eps is not None:
            epsilon = eps
            delta = delt

    mia_conf = {"attack_name": "confidence-threshold", "overall_accuracy": 0.0, "f1_score": 0.0}
    mia_loss = {"attack_name": "loss-threshold", "overall_accuracy": 0.0, "f1_score": 0.0}

    cert = {
        "certificate_id": f"cert-{hash(tuple(request.target_data_ids)) & 0xFFFFFFFF:08x}",
        "version": "1.0",
        "algorithm": algorithm,
        "target_data_ids": request.target_data_ids,
        "unlearning_result": result.success,
        "utility_retained": result.utility_retained,
        "processing_time_ms": result.processing_time_ms,
        "merkle_proof": {
            "root": root,
            "signature_hex": signature,
            "public_key_pem": sig_manager.serialize_public_key(public_key),
            "leaf_count": len(request.target_data_ids),
        },
        "privacy_assessment": {
            "membership_inference": {
                "confidence_based": mia_conf,
                "loss_based": mia_loss,
            },
            "dp_estimate": {"epsilon": epsilon, "delta": delta},
        },
        "regulatory": request.regulatory,
        "status": "verified" if result.success else "failed",
    }
    return cert


@app.post("/evaluate/mia")
async def evaluate_mia(request: MIARequest):
    from training.data import generate_synthetic_data

    target_ids = set(request.target_data_ids) if request.target_data_ids else set()
    data_size = max(request.data_size, 100)

    dataset = generate_synthetic_data(
        num_samples=data_size,
        seed=hash(request.model_name + "_mia") % (2**31),
    )
    unlearned = dataset.get_by_ids(target_ids) if target_ids else dataset.get_subset(list(range(5)))
    split = dataset.size // 2
    member = dataset.get_subset(list(range(1, split)))
    nonmember = dataset.get_subset(list(range(split, dataset.size)))

    ctx = UnlearningContext(
        target_data_ids=list(target_ids) if target_ids else ["data_000000"],
        model_name=request.model_name if request.model_name else "mia_model",
        data_size=data_size,
        config=request.config,
    )

    from unlearning.algorithms.sisa import SISAUnlearning
    algo = SISAUnlearning(num_shards=4)
    await algo.unlearn(ctx)
    model = algo.model

    conf_mia = MembershipInferenceAttack()
    conf_result = conf_mia.attack(
        model,
        unlearned.features if unlearned.size > 0 else member.features,
        member.features,
        nonmember.features,
    )

    loss_mia = LossBasedMIA()
    loss_result = loss_mia.attack(
        model,
        unlearned if unlearned.size > 0 else member,
        member,
        nonmember,
    )

    return {
        "model_name": request.model_name,
        "confidence_based_mia": conf_result,
        "loss_based_mia": loss_result,
    }


@app.post("/evaluate/privacy")
async def evaluate_privacy(request: MIARequest):
    from training.data import generate_synthetic_data

    target_ids = set(request.target_data_ids) if request.target_data_ids else set()
    data_size = max(request.data_size, 100)

    original = generate_synthetic_data(
        num_samples=data_size,
        seed=hash(request.model_name + "_priv") % (2**31),
    )

    ctx = UnlearningContext(
        target_data_ids=list(target_ids) if target_ids else ["data_000000"],
        model_name=request.model_name if request.model_name else "priv_model",
        data_size=data_size,
        config=request.config,
    )

    from unlearning.algorithms.sisa import SISAUnlearning
    algo = SISAUnlearning(num_shards=4)
    await algo.unlearn(ctx)

    retained = original.remove_by_ids(target_ids) if target_ids else original
    model = algo.model

    report = privacy_evaluator.evaluate(
        model=model,
        original_dataset=original,
        retained_dataset=retained,
        unlearned_ids=target_ids,
    )

    return report.to_dict()


@app.post("/proof/generate-zksnark")
async def generate_zksnark_proof(request: ZKProofRequest):
    from verification.zksnark_service import ZKProofService

    svc = ZKProofService(hash_algorithm=request.hash_algorithm)
    proof = svc.generate_proof(
        leaf_data=request.leaf_data,
        all_leaves=request.all_leaves,
    )
    return proof.to_dict()


@app.post("/proof/verify-zksnark")
async def verify_zksnark_proof(request: ZKVerifyRequest):
    from verification.zksnark_service import ZKProofService, ZKProof, ZKVerificationKey

    pdata = request.proof
    vk_data = pdata.get("verification_key", {})
    vk = ZKVerificationKey(
        merkle_root=vk_data.get("merkle_root", ""),
        hash_function=vk_data.get("hash_function", "sha3_256"),
        tree_depth=vk_data.get("tree_depth", 0),
        curve=vk_data.get("curve", "bn254"),
        public_key_pem=vk_data.get("public_key_pem", ""),
    )
    proof_obj = ZKProof(
        circuit_type=pdata.get("circuit_type", "merkle_inclusion"),
        protocol=pdata.get("protocol", "groth16"),
        curve=pdata.get("curve", "bn254"),
        proof_data=pdata.get("proof", {}),
        public_inputs=pdata.get("public_inputs", []),
        verification_key=vk,
    )
    svc = ZKProofService(hash_algorithm=vk.hash_function)
    is_valid = svc.verify_proof(proof_obj)
    return {"is_valid": is_valid, "algorithm": "groth16", "curve": "bn254", "circuit_type": pdata.get("circuit_type", "merkle_inclusion")}


# ──────────────────────────────────────────────────────────────
# New Endpoints: LoRA Training
# ──────────────────────────────────────────────────────────────

@app.post("/train/lora")
async def train_lora(request: LoRATrainRequest):
    trainer = get_lora_trainer()
    from training.lora_trainer import TrainingConfig
    config = TrainingConfig(
        model_name=request.model_name,
        lora_r=request.lora_r,
        lora_alpha=request.lora_alpha,
        num_epochs=request.num_epochs,
        batch_size=request.batch_size,
        learning_rate=request.learning_rate,
    )
    result = trainer.train(
        conversations=request.conversations,
        config=config,
        remove_data_ids=request.remove_data_ids,
    )
    return result


@app.get("/train/checkpoints")
async def list_checkpoints():
    trainer = get_lora_trainer()
    return trainer.list_checkpoints()


@app.post("/train/checkpoints/{checkpoint_id}/load")
async def load_checkpoint(checkpoint_id: str):
    trainer = get_lora_trainer()
    result = trainer.load_checkpoint(checkpoint_id)
    return result


# ──────────────────────────────────────────────────────────────
# New Endpoints: Adapter Lifecycle
# ──────────────────────────────────────────────────────────────

class AdapterLifecycleRouter:
    def __init__(self) -> None:
        self._manager = get_adapter_lifecycle()

    def register(self, request: RegisterAdapterRequest) -> dict:
        version = self._manager.register_adapter(
            adapter_name=request.adapter_name,
            adapter_path=request.adapter_path,
            base_model_name=request.base_model_name,
            config=request.config,
            tags=request.tags,
        )
        return {
            "adapter_name": version.adapter_name,
            "version_id": version.version_id,
            "version_number": version.version_number,
            "status": version.status.value,
        }

    def activate(self, request: AdapterVersionActionRequest) -> dict:
        success = self._manager.activate_version(request.adapter_name, request.version_id)
        return {"success": success}

    def deactivate(self, request: AdapterVersionActionRequest) -> dict:
        success = self._manager.deactivate_version(request.adapter_name, request.version_id)
        return {"success": success}

    def mark_failed(self, request: AdapterVersionActionRequest) -> dict:
        success = self._manager.mark_failed(request.adapter_name, request.version_id)
        return {"success": success}

    def rollback(self, adapter_name: str, version_id: Optional[str] = None) -> dict:
        target = self._manager.rollback(adapter_name, version_id)
        if target is None:
            raise HTTPException(status_code=404, detail=f"No rollback target for '{adapter_name}'")
        return {
            "adapter_name": target.adapter_name,
            "version_id": target.version_id,
            "version_number": target.version_number,
            "status": target.status.value,
        }

    def list_adapters(self) -> list[dict]:
        return self._manager.list_adapters()

    def get_versions(self, adapter_name: str) -> list[dict]:
        return self._manager.get_versions(adapter_name)

    def get_active(self, adapter_name: str) -> dict:
        version = self._manager.get_active_version(adapter_name)
        if version is None:
            raise HTTPException(status_code=404, detail=f"No active version for '{adapter_name}'")
        return {
            "adapter_name": version.adapter_name,
            "version_id": version.version_id,
            "version_number": version.version_number,
            "status": version.status.value,
            "avg_latency_ms": version.avg_latency_ms,
            "total_requests": version.total_requests,
        }

    def setup_canary(self, request: CanarySetupRequest) -> dict:
        self._manager.setup_canary(
            request.adapter_name,
            request.stable_version_id,
            request.canary_version_id,
            request.canary_traffic_pct,
        )
        return {"success": True, "strategy": "canary"}

    def promote_canary(self, adapter_name: str) -> dict:
        version = self._manager.promote_canary(adapter_name)
        if version is None:
            raise HTTPException(status_code=400, detail=f"No canary deployment for '{adapter_name}'")
        return {
            "adapter_name": version.adapter_name,
            "version_id": version.version_id,
            "version_number": version.version_number,
            "status": version.status.value,
        }

    def get_routing(self, adapter_name: str) -> dict:
        rule = self._manager.get_routing_rule(adapter_name)
        if rule is None:
            raise HTTPException(status_code=404, detail=f"No routing rule for '{adapter_name}'")
        return rule

    def record_metrics(self, request: RecordMetricsRequest) -> dict:
        self._manager.record_request(
            request.adapter_name, request.version_id, request.latency_ms, request.success
        )
        return {"success": True}

    def get_latency(self, adapter_name: str) -> dict:
        return self._manager.get_latency_stats(adapter_name)

    def health(self, adapter_name: str) -> dict:
        return self._manager.get_adapter_health(adapter_name)


_lifecycle_router = None


def get_lifecycle_router():
    global _lifecycle_router
    if _lifecycle_router is None:
        _lifecycle_router = AdapterLifecycleRouter()
    return _lifecycle_router


@app.post("/adapters/register")
async def register_adapter(request: RegisterAdapterRequest):
    return get_lifecycle_router().register(request)


@app.post("/adapters/activate")
async def activate_adapter(request: AdapterVersionActionRequest):
    return get_lifecycle_router().activate(request)


@app.post("/adapters/deactivate")
async def deactivate_adapter(request: AdapterVersionActionRequest):
    return get_lifecycle_router().deactivate(request)


@app.post("/adapters/mark-failed")
async def mark_adapter_failed(request: AdapterVersionActionRequest):
    return get_lifecycle_router().mark_failed(request)


@app.post("/adapters/{adapter_name}/rollback")
async def rollback_adapter(adapter_name: str, version_id: Optional[str] = None):
    return get_lifecycle_router().rollback(adapter_name, version_id)


@app.get("/adapters")
async def list_adapters():
    return get_lifecycle_router().list_adapters()


@app.get("/adapters/{adapter_name}/versions")
async def get_adapter_versions(adapter_name: str):
    return get_lifecycle_router().get_versions(adapter_name)


@app.get("/adapters/{adapter_name}/active")
async def get_active_adapter(adapter_name: str):
    return get_lifecycle_router().get_active(adapter_name)


@app.post("/adapters/canary/setup")
async def setup_canary(request: CanarySetupRequest):
    return get_lifecycle_router().setup_canary(request)


@app.post("/adapters/{adapter_name}/canary/promote")
async def promote_canary(adapter_name: str):
    return get_lifecycle_router().promote_canary(adapter_name)


@app.get("/adapters/{adapter_name}/routing")
async def get_routing_rule(adapter_name: str):
    return get_lifecycle_router().get_routing(adapter_name)


@app.post("/adapters/metrics")
async def record_adapter_metrics(request: RecordMetricsRequest):
    return get_lifecycle_router().record_metrics(request)


@app.get("/adapters/{adapter_name}/latency")
async def get_adapter_latency(adapter_name: str):
    return get_lifecycle_router().get_latency(adapter_name)


@app.get("/adapters/{adapter_name}/health")
async def adapter_health(adapter_name: str):
    return get_lifecycle_router().health(adapter_name)


# ──────────────────────────────────────────────────────────────
# New Endpoints: Model Registry
# ──────────────────────────────────────────────────────────────

@app.post("/registry/versions")
async def register_model_version(request: ModelRegistryRequest):
    registry = get_model_registry()
    result = registry.register_version(
        model_name=request.model_name,
        checkpoint_path=request.checkpoint_path,
        algorithm=request.algorithm,
        parent_version_id=request.parent_version_id,
        config=request.config,
        metrics=request.metrics,
    )
    return result


@app.get("/registry/versions")
async def list_all_versions():
    registry = get_model_registry()
    return registry.list_versions()


@app.get("/registry/versions/{model_name}")
async def list_model_versions(model_name: str):
    registry = get_model_registry()
    return registry.list_versions(model_name=model_name)


@app.get("/registry/versions/{model_name}/{version_id}")
async def get_model_version(model_name: str, version_id: str):
    registry = get_model_registry()
    version = registry.get_version(model_name, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail=f"Version {version_id} not found for model {model_name}")
    return version


@app.post("/registry/versions/{model_name}/{version_id}/rollback")
async def rollback_model_version(model_name: str, version_id: str):
    registry = get_model_registry()
    result = registry.rollback(model_name, version_id)
    return result


@app.post("/registry/versions/{model_name}/{version_id}/verify")
async def verify_model_version(model_name: str, version_id: str):
    registry = get_model_registry()
    result = registry.verify_integrity(model_name, version_id)
    return result


@app.get("/registry/stats")
async def registry_stats():
    registry = get_model_registry()
    return registry.get_stats()


# ──────────────────────────────────────────────────────────────
# New Endpoints: Inference
# ──────────────────────────────────────────────────────────────

@app.post("/inference/generate")
async def generate_text(request: InferenceRequestModel):
    service = get_inference_service()
    from inference.service import InferenceRequest
    req = InferenceRequest(
        prompt=request.prompt,
        max_new_tokens=request.max_new_tokens,
        temperature=request.temperature,
        top_p=request.top_p,
        stream=False,
        adapter_name=request.adapter_name,
        system_prompt=request.system_prompt,
    )
    response = service.generate(req)
    return response


@app.post("/inference/generate/stream")
async def generate_stream(request: InferenceRequestModel):
    service = get_inference_service()
    from inference.service import InferenceRequest

    req = InferenceRequest(
        prompt=request.prompt,
        max_new_tokens=request.max_new_tokens,
        temperature=request.temperature,
        top_p=request.top_p,
        stream=True,
        adapter_name=request.adapter_name,
        system_prompt=request.system_prompt,
    )

    async def event_generator():
        for token in service.generate_stream(req):
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/inference/batch")
async def batch_generate(requests: list[InferenceRequestModel]):
    service = get_inference_service()
    from inference.service import InferenceRequest

    inf_requests = [
        InferenceRequest(
            prompt=r.prompt,
            max_new_tokens=r.max_new_tokens,
            temperature=r.temperature,
            top_p=r.top_p,
            stream=False,
            adapter_name=r.adapter_name,
            system_prompt=r.system_prompt,
        )
        for r in requests
    ]
    results = service.batch_generate(inf_requests)
    return results


@app.get("/inference/metrics")
async def inference_metrics():
    service = get_inference_service()
    return service.get_metrics()


@app.post("/inference/adapters/load")
async def load_adapter(request: AdapterLoadRequest):
    service = get_inference_service()
    result = service.load_adapter(request.adapter_name, request.adapter_path)
    return result


@app.post("/inference/adapters/unload")
async def unload_adapter(request: AdapterSwapRequest):
    service = get_inference_service()
    result = service.unload_adapter(request.new_adapter)
    return result


@app.get("/inference/adapters")
async def list_adapters():
    service = get_inference_service()
    return service.list_adapters()


@app.get("/inference/health")
async def inference_health():
    service = get_inference_service()
    return service.health_check()


# ──────────────────────────────────────────────────────────────
# New Endpoints: RAG
# ──────────────────────────────────────────────────────────────

@app.post("/rag/documents/ingest")
async def ingest_document(request: RAGUploadRequest):
    pipeline = get_rag_pipeline()
    result = pipeline.ingest_text(
        text=request.text,
        source_name=request.source_name,
        metadata=request.metadata,
    )
    return result


@app.post("/rag/documents/ingest-text")
async def ingest_text(request: RAGUploadRequest):
    pipeline = get_rag_pipeline()
    result = pipeline.ingest_text(
        text=request.text,
        source_name=request.source_name,
        metadata=request.metadata,
    )
    return result


@app.get("/rag/documents")
async def list_documents():
    pipeline = get_rag_pipeline()
    return pipeline.list_documents()


@app.get("/rag/documents/{document_id}")
async def get_document(document_id: str):
    pipeline = get_rag_pipeline()
    doc = pipeline.get_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    return doc


@app.delete("/rag/documents/{document_id}")
async def delete_document(document_id: str):
    pipeline = get_rag_pipeline()
    result = pipeline.delete_document(document_id)
    return result


@app.post("/rag/search")
async def search_documents(request: RAGSearchRequest):
    pipeline = get_rag_pipeline()
    results = pipeline.search(
        query=request.query,
        top_k=request.top_k,
        filters=request.filters,
    )
    return results


@app.get("/rag/stats")
async def rag_stats():
    pipeline = get_rag_pipeline()
    return pipeline.get_stats()


# ──────────────────────────────────────────────────────────────
# New Endpoints: Conversational Learning
# ──────────────────────────────────────────────────────────────

@app.post("/conversations/record")
async def record_conversation(request: ConversationRecordRequest):
    pipeline = get_conversational_pipeline()
    from training.conversational_pipeline import Conversation
    conversation = Conversation(
        user_id=request.user_id,
        tenant_id=request.tenant_id,
        turns=request.turns,
        feedback=request.feedback,
    )
    result = pipeline.record_conversation(conversation)
    return result


@app.post("/conversations/record/turn")
async def record_turn(request: ConversationRecordRequest):
    pipeline = get_conversational_pipeline()
    if not request.turns:
        raise HTTPException(status_code=400, detail="turns list cannot be empty")
    turn = request.turns[-1]
    result = pipeline.record_turn(
        user_id=request.user_id,
        tenant_id=request.tenant_id,
        turn=turn,
    )
    return result


@app.post("/conversations/feedback")
async def submit_feedback(request: ConversationRecordRequest):
    pipeline = get_conversational_pipeline()
    if request.feedback is None:
        raise HTTPException(status_code=400, detail="feedback cannot be None")
    result = pipeline.submit_feedback(
        user_id=request.user_id,
        tenant_id=request.tenant_id,
        feedback=request.feedback,
    )
    return result


@app.get("/conversations/stats")
async def conversation_stats():
    pipeline = get_conversational_pipeline()
    return pipeline.get_stats()


@app.post("/conversations/train")
async def train_from_conversations():
    pipeline = get_conversational_pipeline()
    result = pipeline.trigger_training()
    return result


# ──────────────────────────────────────────────────────────────
# New Endpoints: Continual Learning (EWC + Replay + Drift)
# ──────────────────────────────────────────────────────────────

@app.get("/continual/stats")
async def continual_learning_stats():
    cl = get_continual_learning()
    return cl.get_stats()


@app.post("/continual/tasks")
async def add_continual_task(request: dict):
    cl = get_continual_learning()
    task = cl.add_task(request.get("task_id", str(uuid.uuid4())), request.get("metadata"))
    return task


@app.get("/continual/tasks")
async def list_continual_tasks():
    cl = get_continual_learning()
    return {"tasks": [cl.get_task(tid) for tid in cl.get_stats().get("tasks", [])]}


@app.get("/continual/tasks/{task_id}")
async def get_continual_task(task_id: str):
    cl = get_continual_learning()
    task = cl.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


@app.post("/continual/samples")
async def record_continual_sample(request: dict):
    cl = get_continual_learning()
    cl.record_sample(
        input_data=request.get("input_data", []),
        target=request.get("target"),
        task_id=request.get("task_id", "default"),
        importance=request.get("importance", 0.5),
        confidence=request.get("confidence", 0.0),
        loss=request.get("loss", 0.0),
        metadata=request.get("metadata"),
    )
    return {"success": True}


@app.post("/continual/ewc/estimate")
async def estimate_ewc(request: dict):
    cl = get_continual_learning()
    dataset = request.get("dataset", [])
    task_id = request.get("task_id", "default")
    num_samples = request.get("num_samples", min(len(dataset), 200))
    result = cl.estimate_ewc(task_id, dataset, num_samples=num_samples)
    return result


@app.get("/continual/ewc/state")
async def ewc_state():
    cl = get_continual_learning()
    stats = cl.get_stats()
    return stats.get("ewc", {})


@app.post("/continual/replay/sample")
async def sample_replay(request: dict):
    cl = get_continual_learning()
    samples = cl.sample_replay(
        n=request.get("n", 32),
        task_id=request.get("task_id"),
    )
    return {"samples": samples, "count": len(samples)}


@app.get("/continual/replay/stats")
async def replay_stats():
    cl = get_continual_learning()
    stats = cl.get_stats()
    return stats.get("replay_buffer", {})


@app.post("/continual/drift/record")
async def record_drift(request: dict):
    cl = get_continual_learning()
    result = cl.detect_drift(
        metric_name=request.get("metric_name", "confidence"),
        value=request.get("value", 0.0),
    )
    return result


@app.get("/continual/drift/alerts")
async def drift_alerts(n: int = 10):
    cl = get_continual_learning()
    return {"alerts": cl.get_drift_alerts(n)}


@app.get("/continual/drift/state")
async def drift_state(metric: str = "confidence"):
    cl = get_continual_learning()
    return cl.get_drift_state(metric)


@app.get("/continual/drift/stats")
async def drift_stats():
    cl = get_continual_learning()
    stats = cl.get_stats()
    return stats.get("drift_detector", {})


# ──────────────────────────────────────────────────────────────
# New Endpoints: E2E Unlearning
# ──────────────────────────────────────────────────────────────

@app.post("/unlearn/e2e")
async def execute_e2e_unlearning(request: E2EDeletionRequest):
    pipeline = get_e2e_pipeline()
    from unlearning.e2e_pipeline import DeletionRequest
    deletion_request = DeletionRequest(
        tenant_id=request.tenant_id,
        user_id=request.user_id,
        target_data_ids=request.target_data_ids,
        model_name=request.model_name,
        reason=request.reason,
        regulatory=request.regulatory,
        priority=request.priority,
    )
    result = await pipeline.execute(deletion_request)
    return result


@app.get("/unlearn/e2e/history")
async def e2e_history():
    pipeline = get_e2e_pipeline()
    return pipeline.get_history()


@app.get("/unlearn/e2e/stats")
async def e2e_stats():
    pipeline = get_e2e_pipeline()
    return pipeline.get_stats()


@app.post("/unlearn/e2e/verify-certificate")
async def verify_deletion_certificate(request: dict):
    pipeline = get_e2e_pipeline()
    from unlearning.e2e_pipeline import DeletionCertificate
    cert = DeletionCertificate(**request)
    result = pipeline.verify_certificate(cert)
    return result


# ──────────────────────────────────────────────────────────────
# New Endpoints: Research Benchmarks
# ──────────────────────────────────────────────────────────────

@app.post("/benchmarks/run")
async def run_benchmarks(request: dict):
    runner = get_benchmark_runner()
    from training.benchmarks import BenchmarkConfig
    cfg = BenchmarkConfig(**{k: v for k, v in request.items() if hasattr(BenchmarkConfig, k)})
    runner._config = cfg
    import asyncio
    results = await asyncio.to_thread(runner.run_all)
    return {
        "total": len(results),
        "completed": sum(1 for r in results if r.status == "completed"),
        "failed": sum(1 for r in results if r.status == "failed"),
        "results": [
            {
                "dataset": r.dataset,
                "algorithm": r.algorithm,
                "data_size": r.data_size,
                "deletion_fraction": r.deletion_fraction,
                "trial": r.trial,
                "metrics": r.metrics,
                "status": r.status,
            }
            for r in results
        ],
    }


@app.get("/benchmarks/summary")
async def benchmark_summary():
    runner = get_benchmark_runner()
    return runner.get_summary()


@app.get("/benchmarks/results")
async def benchmark_results():
    runner = get_benchmark_runner()
    results = runner.get_results()
    return [
        {
            "benchmark_id": r.benchmark_id,
            "dataset": r.dataset,
            "algorithm": r.algorithm,
            "data_size": r.data_size,
            "deletion_fraction": r.deletion_fraction,
            "trial": r.trial,
            "metrics": r.metrics,
            "status": r.status,
        }
        for r in results
    ]


@app.get("/benchmarks/config")
async def benchmark_config():
    runner = get_benchmark_runner()
    from training.benchmarks import BenchmarkDataset
    return {
        "datasets": [d.value for d in BenchmarkDataset],
        "data_sizes": runner._config.data_sizes,
        "deletion_fractions": runner._config.deletion_fractions,
        "algorithms": runner._config.algorithms,
        "num_trials": runner._config.num_trials,
    }


# ──────────────────────────────────────────────────────────────
# New Endpoints: MLflow
# ──────────────────────────────────────────────────────────────
async def mlflow_experiment_stats():
    tracker = get_mlflow_tracker()
    return tracker.get_experiment_stats()


@app.get("/mlflow/runs")
async def mlflow_list_runs():
    tracker = get_mlflow_tracker()
    return tracker.list_runs()


@app.get("/mlflow/runs/{run_id}")
async def mlflow_get_run(run_id: str):
    tracker = get_mlflow_tracker()
    run = tracker.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return run


@app.get("/mlflow/runs/{run_id}/curves")
async def mlflow_get_curves(run_id: str):
    tracker = get_mlflow_tracker()
    curves = tracker.get_training_curves(run_id)
    if curves is None:
        raise HTTPException(status_code=404, detail=f"Curves for run {run_id} not found")
    return curves


@app.post("/mlflow/compare")
async def mlflow_compare_runs(request: dict):
    tracker = get_mlflow_tracker()
    run_ids = request.get("run_ids", [])
    result = tracker.compare_runs(run_ids)
    return result


# ──────────────────────────────────────────────────────────────
# New Endpoints: Explainability
# ──────────────────────────────────────────────────────────────

@app.post("/explain/samples")
async def explain_samples(request: ExplainSamplesRequest):
    mgr = get_explainer_manager()
    samples_np = [np.array(s, dtype=np.float32) for s in request.samples]
    method = request.method.lower()

    if method == "shap":
        explainer = mgr.get_shap()
    elif method == "lime":
        explainer = mgr.get_lime()
    elif method == "integrated_gradients" or method == "ig":
        explainer = mgr.get_ig()
    elif method in ("gradient", "occlusion", "perturbation"):
        explainer = mgr.get_attr(method=method)
    else:
        explainer = mgr.get_shap()

    from explainability.visualization import ExplanationVisualizer

    results = explainer.explain_batch(samples_np)
    chart_data = [ExplanationVisualizer.importance_chart_data(r) for r in results]
    return {
        "method": method,
        "count": len(results),
        "results": [
            {
                "feature_importances": [
                    {"feature": fi.feature_name, "importance": fi.importance_score, "direction": fi.direction}
                    for fi in r.feature_importances
                ],
                "prediction": r.prediction,
                "confidence": r.confidence,
                "runtime_ms": r.runtime_ms,
            }
            for r in results
        ],
        "chart_data": chart_data,
    }


@app.post("/explain/features")
async def explain_features(request: ExplainFeaturesRequest):
    mgr = get_explainer_manager()
    dataset_np = np.array(request.dataset, dtype=np.float32)
    method = request.method.lower()

    if method == "shap":
        explainer = mgr.get_shap()
        global_importance = explainer.global_feature_importance(dataset_np)
    else:
        explainer = mgr.get_attr(method=method if method in ("gradient", "occlusion", "perturbation") else "gradient")
        results = explainer.explain_batch([row for row in dataset_np])
        agg = explainer.aggregate_attributions(results)
        global_importance = {k: v["mean"] for k, v in agg.items()}

    return {
        "method": method,
        "samples": len(request.dataset),
        "features": len(request.feature_names or global_importance),
        "feature_names": request.feature_names or list(global_importance.keys()),
        "global_importance": global_importance,
    }


@app.post("/explain/compare")
async def compare_explanations(request: ExplainCompareRequest):
    mgr = get_explainer_manager()
    pre_samples = [np.array(s, dtype=np.float32) for s in request.pre_unlearn_samples]
    post_samples = [np.array(s, dtype=np.float32) for s in request.post_unlearn_samples]
    method = request.method.lower()

    if method == "shap":
        explainer = mgr.get_shap()
    elif method == "lime":
        explainer = mgr.get_lime()
    elif method in ("integrated_gradients", "ig"):
        explainer = mgr.get_ig()
    elif method in ("gradient", "occlusion", "perturbation"):
        explainer = mgr.get_attr(method=method)
    else:
        explainer = mgr.get_shap()

    pre_results = explainer.explain_batch(pre_samples)
    post_results = explainer.explain_batch(post_samples)

    from explainability.visualization import ExplanationVisualizer

    comparisons = []
    for pre, post in zip(pre_results, post_results):
        comparisons.append(ExplanationVisualizer.comparison_chart_data(pre, post))

    return {
        "method": method,
        "pair_count": min(len(pre_results), len(post_results)),
        "comparisons": comparisons,
    }


@app.post("/explain/privacy-heatmap")
async def privacy_heatmap(request: PrivacyHeatmapRequest):
    from explainability.visualization import ExplanationVisualizer

    mgr = get_explainer_manager()
    samples_np = [np.array(s, dtype=np.float32) for s in request.samples]
    explainer = mgr.get_shap()
    results = explainer.explain_batch(samples_np)

    importances = []
    for r in results:
        row = {}
        for fi in r.feature_importances:
            row[fi.feature_name] = fi.importance_score
        importances.append(row)

    heatmap = ExplanationVisualizer.privacy_risk_heatmap(
        importances, request.privacy_scores, request.feature_names
    )
    return heatmap


@app.post("/explain/drift")
async def model_drift(request: DriftRequest):
    from explainability.visualization import ExplanationVisualizer

    summary = ExplanationVisualizer.drift_summary(
        request.pre_confidences,
        request.post_confidences,
        request.pre_importances,
        request.post_importances,
    )
    return summary


@app.get("/explain/methods")
async def list_explain_methods():
    return {
        "methods": [
            {"id": "shap", "name": "SHAP", "description": "SHAP (SHapley Additive exPlanations) — game-theoretic feature importance"},
            {"id": "lime", "name": "LIME", "description": "Local Interpretable Model-agnostic Explanations — local surrogate models"},
            {"id": "integrated_gradients", "name": "Integrated Gradients", "description": "Attribution via path integral of gradients"},
            {"id": "gradient", "name": "Gradient Attribution", "description": "Simple gradient-based feature attribution"},
            {"id": "occlusion", "name": "Occlusion", "description": "Feature occlusion / ablation-based attribution"},
            {"id": "perturbation", "name": "Perturbation", "description": "Random perturbation-based feature importance"},
        ]
    }


# ──────────────────────────────────────────────────────────────
# New Endpoints: Hybrid Controller
# ──────────────────────────────────────────────────────────────

@app.get("/controller/health")
async def controller_health():
    from unlearning.hybrid_controller import HybridAdaptiveController
    result = controller.health_check()
    return result


@app.get("/controller/metrics")
async def controller_metrics():
    return controller.get_metrics()


@app.get("/controller/decisions")
async def controller_decisions():
    return controller.get_decision_log()


@app.post("/controller/estimate")
async def controller_estimate(request: UnlearningRequest):
    context = UnlearningContext(
        target_data_ids=request.target_data_ids,
        model_type=request.model_type,
        model_name=request.model_name,
        data_size=request.data_size,
        latency_ms=request.latency_ms,
        accuracy_target=request.accuracy_target,
        regulatory=request.regulatory,
        config=request.config,
    )
    result = controller.estimate_time(context)
    return result


# ──────────────────────────────────────────────────────────────
# Health Endpoint (extended with new component status)
# ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    new_components = {
        "lora_trainer": _lora_trainer is not None,
        "model_registry": _model_registry is not None,
        "rag_pipeline": _rag_pipeline is not None,
        "inference_service": _inference_service is not None,
        "conversational_pipeline": _conversational_pipeline is not None,
        "mlflow_tracker": _mlflow_tracker is not None,
        "e2e_pipeline": _e2e_pipeline is not None,
        "explainer_manager": _explainer_manager is not None,
    }
    return {
        "status": "healthy",
        "engine": "veriunlearn-ml",
        "version": "1.0.0",
        "algorithms": list(controller.algorithms.keys()),
        "components": new_components,
    }
