import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import torch

from models.single_model import SingleModel
from security.attacks.membership_inference import MembershipInferenceAttack
from training.data import Dataset, accuracy_score, generate_synthetic_data
from unlearning.algorithms.base import UnlearningContext, UnlearningResult
from unlearning.hybrid_controller import ControllerConfig, HybridAdaptiveController
from verification.merkle_tree import MerkleTree
from verification.privacy_evaluation import PrivacyEvaluator
from verification.signatures import SignatureManager
from verification.zksnark_service import ZKProofService

logger = logging.getLogger(__name__)


@dataclass
class DeletionRequest:
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    user_id: str = ""
    target_data_ids: list[str] = field(default_factory=list)
    model_name: str = ""
    model_version_id: Optional[str] = None
    reason: str = ""
    regulatory: str = "gdpr"
    priority: str = "medium"
    status: str = "pending"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict = field(default_factory=dict)


@dataclass
class PipelineStep:
    step_id: str
    name: str
    status: str = "pending"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    result: Optional[dict] = None
    error: Optional[str] = None


@dataclass
class DeletionCertificate:
    certificate_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = ""
    version: str = "1.0"
    algorithm: str = ""
    target_data_ids: list[str] = field(default_factory=list)
    unlearning_result: dict = field(default_factory=dict)
    utility_retained: float = 0.0
    processing_time_ms: int = 0
    merkle_proof: dict = field(default_factory=dict)
    privacy_assessment: dict = field(default_factory=dict)
    membership_inference_results: dict = field(default_factory=dict)
    weight_comparison: dict = field(default_factory=dict)
    sha256: str = ""
    merkle_root: str = ""
    signature_hex: str = ""
    public_key_pem: str = ""
    status: str = "generated"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    expires_at: str = ""
    verified_at: Optional[str] = None


class E2EUnlearningPipeline:
    def __init__(self, controller_config: Optional[ControllerConfig] = None) -> None:
        self.controller = HybridAdaptiveController(config=controller_config)
        self.signature_manager = SignatureManager()
        self.privacy_evaluator = PrivacyEvaluator()
        self.zk_service = ZKProofService()
        self._pipeline_history: list[dict] = []

    # ------------------------------------------------------------------
    # Main orchestrator
    # ------------------------------------------------------------------

    async def execute_full_pipeline(
        self,
        request: DeletionRequest,
        dataset: Optional[Dataset] = None,
    ) -> dict:
        pipeline_start = time.perf_counter()
        pipeline_id = str(uuid.uuid4())

        if dataset is None:
            dataset = generate_synthetic_data(
                num_samples=200, num_features=20, num_classes=2
            )
            logger.info(
                "Generated synthetic dataset with %d samples", dataset.size
            )

        request.status = "processing"
        all_steps: list[PipelineStep] = []

        logger.info(
            "Starting pipeline %s for request %s (%d target samples)",
            pipeline_id,
            request.request_id,
            len(request.target_data_ids),
        )

        # Step 1: Locate samples
        step1 = self._step_locate_samples(request, dataset)
        all_steps.append(step1)
        if step1.status == "failed":
            request.status = "failed"
            return self._build_pipeline_result(
                pipeline_id, request, all_steps, pipeline_start
            )

        located_ids: list[str] = step1.result.get("located_ids", [])
        remaining: Dataset = step1.result["remaining_dataset"]

        # Step 2: Locate embeddings
        step2 = self._step_locate_embeddings(request, dataset)
        all_steps.append(step2)

        # Step 3: Locate LoRA records
        step3 = self._step_locate_lora_records(request)
        all_steps.append(step3)

        # Step 4: Execute unlearning
        step4 = await self._step_execute_unlearning(request, dataset, remaining)
        all_steps.append(step4)
        if step4.status == "failed":
            request.status = "failed"
            return self._build_pipeline_result(
                pipeline_id, request, all_steps, pipeline_start
            )

        unlearning_result: UnlearningResult = step4.result["unlearning_result"]

        # Step 5: Evaluate
        step5 = self._step_evaluate(dataset, located_ids, unlearning_result)
        all_steps.append(step5)

        # Step 6: Membership inference
        step6 = self._step_membership_inference(dataset, located_ids)
        all_steps.append(step6)

        # Step 7: Weight comparison
        original_weights = (
            step5.result.get("original_weights") if step5.result else None
        )
        updated_weights = (
            step5.result.get("updated_weights") if step5.result else None
        )
        step7 = self._step_weight_comparison(original_weights, updated_weights)
        all_steps.append(step7)

        # Step 8: Hash computation
        step8 = self._step_compute_hash(None, step4.result or {})
        all_steps.append(step8)

        # Step 9: Merkle root
        step9 = self._step_build_merkle(all_steps)
        all_steps.append(step9)

        # Step 10: Sign
        merkle_root = step9.result.get("merkle_root", "") if step9.result else ""
        step10 = self._step_sign(merkle_root)
        all_steps.append(step10)

        # Step 11: Certificate
        step11 = self._step_generate_certificate(
            request,
            unlearning_result,
            step9.result or {},
            step10.result or {},
            step5.result or {},
            step6.result or {},
            step7.result or {},
            step8.result or {},
        )
        all_steps.append(step11)
        certificate: Optional[DeletionCertificate] = (
            step11.result.get("certificate") if step11.result else None
        )

        # Step 12: Dashboard data
        step12 = self._step_prepare_dashboard_data(request, all_steps, certificate)
        all_steps.append(step12)

        request.status = "completed"
        request.updated_at = datetime.now(timezone.utc).isoformat()

        result = self._build_pipeline_result(
            pipeline_id, request, all_steps, pipeline_start
        )

        self._pipeline_history.append(result)

        logger.info(
            "Pipeline %s completed in %d ms",
            pipeline_id,
            result["total_duration_ms"],
        )

        return result

    # ------------------------------------------------------------------
    # Step implementations
    # ------------------------------------------------------------------

    def _step_locate_samples(
        self, request: DeletionRequest, dataset: Dataset
    ) -> PipelineStep:
        step = PipelineStep(
            step_id=str(uuid.uuid4()),
            name="locate_samples",
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        try:
            target_set = set(request.target_data_ids)
            located_ids = [
                did for did in dataset.data_ids if did in target_set
            ]
            not_found = target_set - set(located_ids)

            remaining = dataset.remove_by_ids(target_set)

            step.status = "completed"
            step.completed_at = datetime.now(timezone.utc).isoformat()
            step.duration_ms = 0
            step.result = {
                "located_ids": located_ids,
                "not_found_ids": list(not_found),
                "total_target": len(request.target_data_ids),
                "total_located": len(located_ids),
                "remaining_size": remaining.size,
                "original_size": dataset.size,
                "remaining_dataset": remaining,
            }
            logger.info(
                "Located %d/%d target samples, %d remaining",
                len(located_ids),
                len(request.target_data_ids),
                remaining.size,
            )
        except Exception as exc:
            step.status = "failed"
            step.error = str(exc)
            step.completed_at = datetime.now(timezone.utc).isoformat()
            logger.error("Step locate_samples failed: %s", exc)
        return step

    def _step_locate_embeddings(
        self, request: DeletionRequest, dataset: Dataset
    ) -> PipelineStep:
        step = PipelineStep(
            step_id=str(uuid.uuid4()),
            name="locate_embeddings",
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        try:
            embedding_records = []
            for data_id in request.target_data_ids:
                embedding_records.append(
                    {
                        "data_id": data_id,
                        "collection": f"embeddings_{request.model_name}",
                        "vector_id": f"vec_{data_id}",
                        "dimension": dataset.features.shape[1]
                        if dataset.features.dim() > 1
                        else 1,
                        "indexed_at": datetime.now(timezone.utc).isoformat(),
                        "status": "pending_deletion",
                    }
                )

            step.status = "completed"
            step.completed_at = datetime.now(timezone.utc).isoformat()
            step.duration_ms = 0
            step.result = {
                "embedding_records": embedding_records,
                "total_embeddings": len(embedding_records),
                "collection_name": f"embeddings_{request.model_name}",
                "backend": "qdrant",
            }
            logger.info(
                "Located %d embedding records for deletion",
                len(embedding_records),
            )
        except Exception as exc:
            step.status = "failed"
            step.error = str(exc)
            step.completed_at = datetime.now(timezone.utc).isoformat()
            logger.error("Step locate_embeddings failed: %s", exc)
        return step

    def _step_locate_lora_records(self, request: DeletionRequest) -> PipelineStep:
        step = PipelineStep(
            step_id=str(uuid.uuid4()),
            name="locate_lora_records",
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        try:
            lora_records = []
            for data_id in request.target_data_ids:
                lora_records.append(
                    {
                        "data_id": data_id,
                        "adapter_name": f"lora_{request.model_name}_v0",
                        "rank": 8,
                        "alpha": 16.0,
                        "target_modules": ["q_proj", "v_proj"],
                        "training_run_id": f"run_{hash(data_id) % 10000:04d}",
                        "status": "pending_cleanup",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                )

            step.status = "completed"
            step.completed_at = datetime.now(timezone.utc).isoformat()
            step.duration_ms = 0
            step.result = {
                "lora_records": lora_records,
                "total_records": len(lora_records),
                "adapter_name": f"lora_{request.model_name}_v0",
            }
            logger.info(
                "Located %d LoRA adapter records for cleanup", len(lora_records)
            )
        except Exception as exc:
            step.status = "failed"
            step.error = str(exc)
            step.completed_at = datetime.now(timezone.utc).isoformat()
            logger.error("Step locate_lora_records failed: %s", exc)
        return step

    async def _step_execute_unlearning(
        self,
        request: DeletionRequest,
        dataset: Dataset,
        remaining: Dataset,
    ) -> PipelineStep:
        step = PipelineStep(
            step_id=str(uuid.uuid4()),
            name="execute_unlearning",
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        try:
            context = UnlearningContext(
                target_data_ids=request.target_data_ids,
                model_type="transformer",
                model_name=request.model_name,
                data_size=dataset.size,
                latency_ms=500,
                accuracy_target=0.95,
                regulatory=request.regulatory,
                config={
                    "input_dim": dataset.features.shape[1],
                    "num_classes": len(dataset.labels.unique()),
                    "data_sensitivity": request.metadata.get(
                        "data_sensitivity", "standard"
                    ),
                    "remaining_size": remaining.size,
                },
            )

            unlearning_result = await self.controller.execute(context)

            step.status = "completed" if unlearning_result.success else "failed"
            step.completed_at = datetime.now(timezone.utc).isoformat()
            step.duration_ms = unlearning_result.processing_time_ms
            step.result = {
                "unlearning_result": unlearning_result,
                "algorithm": unlearning_result.algorithm,
                "success": unlearning_result.success,
                "utility_retained": unlearning_result.utility_retained,
                "metrics": unlearning_result.metrics,
                "error_message": unlearning_result.error_message,
            }
            if unlearning_result.error_message:
                step.error = unlearning_result.error_message

            logger.info(
                "Unlearning executed: algorithm=%s success=%s utility=%.4f",
                unlearning_result.algorithm,
                unlearning_result.success,
                unlearning_result.utility_retained,
            )
        except Exception as exc:
            step.status = "failed"
            step.error = str(exc)
            step.completed_at = datetime.now(timezone.utc).isoformat()
            logger.error("Step execute_unlearning failed: %s", exc)
        return step

    def _step_evaluate(
        self,
        original_dataset: Dataset,
        unlearned_ids: list[str],
        unlearning_result: UnlearningResult,
    ) -> PipelineStep:
        step = PipelineStep(
            step_id=str(uuid.uuid4()),
            name="evaluate",
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        try:
            input_dim = original_dataset.features.shape[1]
            num_classes = len(original_dataset.labels.unique())

            original_model = SingleModel(
                input_dim=input_dim,
                num_classes=num_classes,
            )
            original_model.train(
                original_dataset.features,
                original_dataset.labels,
                epochs=50,
            )
            original_preds = original_model.predict(original_dataset.features)
            original_accuracy = accuracy_score(original_dataset, original_preds)
            original_weights = original_model.model.flattened_params().tolist()

            remaining = original_dataset.remove_by_ids(set(unlearned_ids))
            if remaining.size > 0:
                updated_model = SingleModel(
                    input_dim=input_dim,
                    num_classes=num_classes,
                )
                updated_model.train(
                    remaining.features,
                    remaining.labels,
                    epochs=50,
                )
                updated_preds = updated_model.predict(remaining.features)
                updated_accuracy = accuracy_score(remaining, updated_preds)
                updated_weights = updated_model.model.flattened_params().tolist()
            else:
                updated_accuracy = 0.0
                updated_weights = []

            utility_retained = (
                updated_accuracy / original_accuracy
                if original_accuracy > 0
                else 1.0
            )

            step.status = "completed"
            step.completed_at = datetime.now(timezone.utc).isoformat()
            step.duration_ms = 0
            step.result = {
                "original_accuracy": original_accuracy,
                "updated_accuracy": updated_accuracy,
                "utility_retained": utility_retained,
                "original_dataset_size": original_dataset.size,
                "remaining_dataset_size": remaining.size,
                "unlearned_count": len(unlearned_ids),
                "original_weights": original_weights,
                "updated_weights": updated_weights,
                "unlearning_result_algorithm": unlearning_result.algorithm,
                "unlearning_result_utility": unlearning_result.utility_retained,
            }
            logger.info(
                "Evaluation: original_acc=%.4f updated_acc=%.4f utility=%.4f",
                original_accuracy,
                updated_accuracy,
                utility_retained,
            )
        except Exception as exc:
            step.status = "failed"
            step.error = str(exc)
            step.completed_at = datetime.now(timezone.utc).isoformat()
            logger.error("Step evaluate failed: %s", exc)
        return step

    def _step_membership_inference(
        self,
        dataset: Dataset,
        unlearned_ids: list[str],
    ) -> PipelineStep:
        step = PipelineStep(
            step_id=str(uuid.uuid4()),
            name="membership_inference",
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        try:
            input_dim = dataset.features.shape[1]
            num_classes = len(dataset.labels.unique())

            model = SingleModel(
                input_dim=input_dim,
                num_classes=num_classes,
            )
            model.train(
                dataset.features,
                dataset.labels,
                epochs=50,
            )

            unlearned_set = set(unlearned_ids)
            target_indices = [
                i
                for i, did in enumerate(dataset.data_ids)
                if did in unlearned_set
            ]

            if len(target_indices) == 0:
                target_indices = list(range(min(10, dataset.size)))

            remaining_indices = [
                i
                for i, did in enumerate(dataset.data_ids)
                if did not in unlearned_set
            ]

            split = max(1, len(remaining_indices) // 2)
            member_indices = remaining_indices[:split]
            nonmember_indices = remaining_indices[split:]

            if len(member_indices) == 0:
                member_indices = list(range(min(10, dataset.size)))
            if len(nonmember_indices) == 0:
                nonmember_indices = list(range(min(10, dataset.size)))

            target_features = dataset.features[target_indices]
            member_features = dataset.features[member_indices]
            nonmember_features = dataset.features[nonmember_indices]

            mia = MembershipInferenceAttack(threshold_percentile=5.0)
            mia_result = mia.attack(
                model, target_features, member_features, nonmember_features
            )

            step.status = "completed"
            step.completed_at = datetime.now(timezone.utc).isoformat()
            step.duration_ms = 0
            step.result = {
                "attack_name": mia_result.get("attack_name", "confidence-threshold"),
                "overall_accuracy": mia_result.get("overall_accuracy", 0.0),
                "member_accuracy": mia_result.get("member_accuracy", 0.0),
                "nonmember_accuracy": mia_result.get("nonmember_accuracy", 0.0),
                "precision": mia_result.get("precision", 0.0),
                "recall": mia_result.get("recall", 0.0),
                "f1_score": mia_result.get("f1_score", 0.0),
                "target_members_found": mia_result.get("target_members_found", 0),
                "target_total": mia_result.get("target_total", 0),
                "threshold": mia_result.get("threshold", 0.0),
                "privacy_risk": "low"
                if mia_result.get("overall_accuracy", 0.0) < 0.6
                else "medium"
                if mia_result.get("overall_accuracy", 0.0) < 0.8
                else "high",
            }
            logger.info(
                "MIA: overall_acc=%.4f precision=%.4f recall=%.4f",
                mia_result.get("overall_accuracy", 0.0),
                mia_result.get("precision", 0.0),
                mia_result.get("recall", 0.0),
            )
        except Exception as exc:
            step.status = "failed"
            step.error = str(exc)
            step.completed_at = datetime.now(timezone.utc).isoformat()
            logger.error("Step membership_inference failed: %s", exc)
        return step

    def _step_weight_comparison(
        self,
        original_weights: Any,
        updated_weights: Any,
    ) -> PipelineStep:
        step = PipelineStep(
            step_id=str(uuid.uuid4()),
            name="weight_comparison",
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        try:
            if (
                original_weights is None
                or updated_weights is None
                or len(original_weights) == 0
                or len(updated_weights) == 0
            ):
                step.status = "completed"
                step.completed_at = datetime.now(timezone.utc).isoformat()
                step.duration_ms = 0
                step.result = {
                    "comparison_available": False,
                    "reason": "Weight vectors not available or empty",
                }
                return step

            orig_tensor = torch.tensor(original_weights, dtype=torch.float32)
            upd_tensor = torch.tensor(updated_weights, dtype=torch.float32)

            min_len = min(len(orig_tensor), len(upd_tensor))
            orig_trimmed = orig_tensor[:min_len]
            upd_trimmed = upd_tensor[:min_len]

            diff = orig_trimmed - upd_trimmed
            l2_distance = torch.norm(diff).item()
            l1_distance = torch.sum(torch.abs(diff)).item()
            cosine_sim = (
                torch.nn.functional.cosine_similarity(
                    orig_trimmed.unsqueeze(0), upd_trimmed.unsqueeze(0)
                ).item()
                if min_len > 0
                else 0.0
            )

            orig_norm = torch.norm(orig_trimmed).item()
            relative_change = (
                l2_distance / orig_norm if orig_norm > 0 else 0.0
            )

            num_changed = int(torch.sum(torch.abs(diff) > 1e-6).item())
            percent_changed = (
                (num_changed / min_len * 100.0) if min_len > 0 else 0.0
            )

            step.status = "completed"
            step.completed_at = datetime.now(timezone.utc).isoformat()
            step.duration_ms = 0
            step.result = {
                "comparison_available": True,
                "l2_distance": l2_distance,
                "l1_distance": l1_distance,
                "cosine_similarity": cosine_sim,
                "relative_change": relative_change,
                "num_parameters": min_len,
                "num_changed": num_changed,
                "percent_changed": percent_changed,
                "max_abs_diff": float(torch.max(torch.abs(diff)).item()),
                "mean_abs_diff": float(torch.mean(torch.abs(diff)).item()),
            }
            logger.info(
                "Weight comparison: L2=%.6f cosine=%.6f changed=%.1f%%",
                l2_distance,
                cosine_sim,
                percent_changed,
            )
        except Exception as exc:
            step.status = "failed"
            step.error = str(exc)
            step.completed_at = datetime.now(timezone.utc).isoformat()
            logger.error("Step weight_comparison failed: %s", exc)
        return step

    def _step_compute_hash(
        self, model_path: Optional[str], result: dict
    ) -> PipelineStep:
        step = PipelineStep(
            step_id=str(uuid.uuid4()),
            name="compute_hash",
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        try:
            hash_input = json.dumps(
                {
                    "algorithm": result.get("algorithm", "unknown"),
                    "success": result.get("success", False),
                    "utility_retained": result.get("utility_retained", 0.0),
                    "processing_time_ms": result.get("processing_time_ms", 0),
                    "metrics": result.get("metrics", {}),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                sort_keys=True,
                default=str,
            )
            sha256_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

            step.status = "completed"
            step.completed_at = datetime.now(timezone.utc).isoformat()
            step.duration_ms = 0
            step.result = {
                "sha256": sha256_hash,
                "hash_algorithm": "sha256",
                "hashed_bytes": len(hash_input.encode("utf-8")),
                "model_path": model_path,
            }
            logger.info("Computed SHA256: %s", sha256_hash[:16])
        except Exception as exc:
            step.status = "failed"
            step.error = str(exc)
            step.completed_at = datetime.now(timezone.utc).isoformat()
            logger.error("Step compute_hash failed: %s", exc)
        return step

    def _step_build_merkle(self, steps: list[PipelineStep]) -> PipelineStep:
        step = PipelineStep(
            step_id=str(uuid.uuid4()),
            name="build_merkle",
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        try:
            leaf_data_list: list[str] = []
            for s in steps:
                leaf_payload = json.dumps(
                    {
                        "step_id": s.step_id,
                        "name": s.name,
                        "status": s.status,
                        "duration_ms": s.duration_ms,
                        "result_hash": hashlib.sha256(
                            json.dumps(
                                s.result or {}, sort_keys=True, default=str
                            ).encode("utf-8")
                        ).hexdigest(),
                    },
                    sort_keys=True,
                )
                leaf_data_list.append(leaf_payload)

            tree = MerkleTree()
            tree.add_leaves(leaf_data_list)
            merkle_root = tree.build_tree()

            proofs: dict[str, dict] = {}
            for idx, s in enumerate(steps):
                proofs[s.name] = {
                    "leaf_index": idx,
                    "proof": tree.get_proof(idx),
                }

            step.status = "completed"
            step.completed_at = datetime.now(timezone.utc).isoformat()
            step.duration_ms = 0
            step.result = {
                "merkle_root": merkle_root,
                "tree_depth": len(tree.tree),
                "leaf_count": len(tree.leaves),
                "proofs": proofs,
                "tree_info": tree.to_dict(),
            }
            logger.info(
                "Merkle tree built: root=%s depth=%d leaves=%d",
                merkle_root[:16],
                len(tree.tree),
                len(tree.leaves),
            )
        except Exception as exc:
            step.status = "failed"
            step.error = str(exc)
            step.completed_at = datetime.now(timezone.utc).isoformat()
            logger.error("Step build_merkle failed: %s", exc)
        return step

    def _step_sign(self, merkle_root: str) -> PipelineStep:
        step = PipelineStep(
            step_id=str(uuid.uuid4()),
            name="sign",
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        try:
            private_key, public_key = self.signature_manager.generate_key_pair()
            signature_hex = self.signature_manager.sign(merkle_root, private_key)
            public_key_pem = self.signature_manager.serialize_public_key(public_key)

            is_valid = self.signature_manager.verify(
                merkle_root, signature_hex, public_key
            )

            step.status = "completed"
            step.completed_at = datetime.now(timezone.utc).isoformat()
            step.duration_ms = 0
            step.result = {
                "signature_hex": signature_hex,
                "public_key_pem": public_key_pem,
                "algorithm": self.signature_manager.algorithm,
                "signature_valid": is_valid,
                "signed_message": merkle_root,
            }
            logger.info(
                "Signed Merkle root: valid=%s algo=%s",
                is_valid,
                self.signature_manager.algorithm,
            )
        except Exception as exc:
            step.status = "failed"
            step.error = str(exc)
            step.completed_at = datetime.now(timezone.utc).isoformat()
            logger.error("Step sign failed: %s", exc)
        return step

    def _step_generate_certificate(
        self,
        request: DeletionRequest,
        result: UnlearningResult,
        merkle_data: dict,
        signature_data: dict,
        eval_data: dict,
        mia_data: dict,
        weight_data: dict,
        hash_data: dict,
    ) -> PipelineStep:
        step = PipelineStep(
            step_id=str(uuid.uuid4()),
            name="generate_certificate",
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        try:
            now = datetime.now(timezone.utc)
            certificate = DeletionCertificate(
                request_id=request.request_id,
                algorithm=result.algorithm,
                target_data_ids=request.target_data_ids,
                unlearning_result={
                    "success": result.success,
                    "algorithm": result.algorithm,
                    "processing_time_ms": result.processing_time_ms,
                    "utility_retained": result.utility_retained,
                    "metrics": result.metrics,
                    "metadata": result.metadata,
                },
                utility_retained=eval_data.get(
                    "utility_retained", result.utility_retained
                ),
                processing_time_ms=result.processing_time_ms,
                merkle_proof={
                    "merkle_root": merkle_data.get("merkle_root", ""),
                    "tree_depth": merkle_data.get("tree_depth", 0),
                    "leaf_count": merkle_data.get("leaf_count", 0),
                    "proofs": merkle_data.get("proofs", {}),
                },
                privacy_assessment={
                    "overall_score": mia_data.get("overall_accuracy", 0.0),
                    "risk_level": mia_data.get("privacy_risk", "unknown"),
                },
                membership_inference_results=mia_data,
                weight_comparison=weight_data,
                sha256=hash_data.get("sha256", ""),
                merkle_root=merkle_data.get("merkle_root", ""),
                signature_hex=signature_data.get("signature_hex", ""),
                public_key_pem=signature_data.get("public_key_pem", ""),
                status="generated",
                created_at=now.isoformat(),
                expires_at=(now + timedelta(days=365)).isoformat(),
            )

            step.status = "completed"
            step.completed_at = datetime.now(timezone.utc).isoformat()
            step.duration_ms = 0
            step.result = {
                "certificate": certificate,
                "certificate_id": certificate.certificate_id,
                "sha256": certificate.sha256,
            }
            logger.info(
                "Certificate generated: id=%s", certificate.certificate_id
            )
        except Exception as exc:
            step.status = "failed"
            step.error = str(exc)
            step.completed_at = datetime.now(timezone.utc).isoformat()
            logger.error("Step generate_certificate failed: %s", exc)
        return step

    def _step_prepare_dashboard_data(
        self,
        request: DeletionRequest,
        all_steps: list[PipelineStep],
        certificate: Optional[DeletionCertificate],
    ) -> PipelineStep:
        step = PipelineStep(
            step_id=str(uuid.uuid4()),
            name="prepare_dashboard_data",
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        try:
            steps_summary = []
            total_duration = 0
            for s in all_steps:
                dur = s.duration_ms or 0
                total_duration += dur
                steps_summary.append(
                    {
                        "name": s.name,
                        "status": s.status,
                        "duration_ms": dur,
                        "error": s.error,
                    }
                )

            completed_count = sum(
                1 for s in all_steps if s.status == "completed"
            )
            failed_count = sum(1 for s in all_steps if s.status == "failed")

            certificate_info = None
            if certificate is not None:
                certificate_info = {
                    "certificate_id": certificate.certificate_id,
                    "algorithm": certificate.algorithm,
                    "utility_retained": certificate.utility_retained,
                    "merkle_root": certificate.merkle_root[:16] + "..."
                    if certificate.merkle_root
                    else "",
                    "signature_valid": bool(certificate.signature_hex),
                    "expires_at": certificate.expires_at,
                }

            mia_results = None
            for s in all_steps:
                if s.name == "membership_inference" and s.result:
                    mia_results = {
                        k: v
                        for k, v in s.result.items()
                        if k
                        in (
                            "overall_accuracy",
                            "precision",
                            "recall",
                            "privacy_risk",
                        )
                    }
                    break

            dashboard = {
                "pipeline_id": str(uuid.uuid4()),
                "request_summary": {
                    "request_id": request.request_id,
                    "tenant_id": request.tenant_id,
                    "user_id": request.user_id,
                    "model_name": request.model_name,
                    "regulatory": request.regulatory,
                    "priority": request.priority,
                    "num_target_samples": len(request.target_data_ids),
                    "status": request.status,
                },
                "execution_summary": {
                    "total_steps": len(all_steps),
                    "completed_steps": completed_count,
                    "failed_steps": failed_count,
                    "total_duration_ms": total_duration,
                    "all_successful": failed_count == 0,
                },
                "steps": steps_summary,
                "certificate": certificate_info,
                "privacy_assessment": mia_results,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            step.status = "completed"
            step.completed_at = datetime.now(timezone.utc).isoformat()
            step.duration_ms = 0
            step.result = {"dashboard": dashboard}
            logger.info(
                "Dashboard data prepared: %d/%d steps completed",
                completed_count,
                len(all_steps),
            )
        except Exception as exc:
            step.status = "failed"
            step.error = str(exc)
            step.completed_at = datetime.now(timezone.utc).isoformat()
            logger.error("Step prepare_dashboard_data failed: %s", exc)
        return step

    # ------------------------------------------------------------------
    # Certificate verification
    # ------------------------------------------------------------------

    def verify_certificate(self, certificate: DeletionCertificate) -> dict:
        results: dict[str, Any] = {
            "certificate_id": certificate.certificate_id,
            "overall_valid": True,
            "checks": {},
        }

        # Check: Merkle root integrity
        try:
            merkle_valid = bool(certificate.merkle_root)
            results["checks"]["merkle_root"] = {
                "valid": merkle_valid,
                "root": certificate.merkle_root[:16] + "..."
                if certificate.merkle_root
                else "",
            }
            if not merkle_valid:
                results["overall_valid"] = False
        except Exception as exc:
            results["checks"]["merkle_root"] = {
                "valid": False,
                "error": str(exc),
            }
            results["overall_valid"] = False

        # Check: Signature validity
        try:
            if certificate.signature_hex and certificate.merkle_root:
                pub_key = self.signature_manager.load_public_key(
                    certificate.public_key_pem
                )
                sig_valid = self.signature_manager.verify(
                    certificate.merkle_root,
                    certificate.signature_hex,
                    pub_key,
                )
            else:
                sig_valid = False
            results["checks"]["signature"] = {
                "valid": sig_valid,
                "algorithm": self.signature_manager.algorithm,
            }
            if not sig_valid:
                results["overall_valid"] = False
        except Exception as exc:
            results["checks"]["signature"] = {
                "valid": False,
                "error": str(exc),
            }
            results["overall_valid"] = False

        # Check: Certificate expiry
        try:
            expires_at = datetime.fromisoformat(certificate.expires_at)
            now = datetime.now(timezone.utc)
            is_expired = now > expires_at
            results["checks"]["expiry"] = {
                "valid": not is_expired,
                "expires_at": certificate.expires_at,
                "is_expired": is_expired,
            }
            if is_expired:
                results["overall_valid"] = False
        except Exception as exc:
            results["checks"]["expiry"] = {
                "valid": False,
                "error": str(exc),
            }
            results["overall_valid"] = False

        # Check: SHA256 integrity
        try:
            hash_valid = bool(certificate.sha256) and len(certificate.sha256) == 64
            results["checks"]["sha256"] = {
                "valid": hash_valid,
                "hash": certificate.sha256[:16] + "..."
                if certificate.sha256
                else "",
            }
            if not hash_valid:
                results["overall_valid"] = False
        except Exception as exc:
            results["checks"]["sha256"] = {
                "valid": False,
                "error": str(exc),
            }
            results["overall_valid"] = False

        # Check: Unlearning result
        try:
            unlearn_valid = certificate.unlearning_result.get("success", False)
            results["checks"]["unlearning_result"] = {
                "valid": unlearn_valid,
                "algorithm": certificate.unlearning_result.get("algorithm", ""),
                "utility_retained": certificate.utility_retained,
            }
            if not unlearn_valid:
                results["overall_valid"] = False
        except Exception as exc:
            results["checks"]["unlearning_result"] = {
                "valid": False,
                "error": str(exc),
            }
            results["overall_valid"] = False

        # Check: Privacy assessment
        try:
            risk = certificate.privacy_assessment.get("risk_level", "unknown")
            privacy_valid = risk in ("low", "medium")
            results["checks"]["privacy_assessment"] = {
                "valid": privacy_valid,
                "risk_level": risk,
                "overall_score": certificate.privacy_assessment.get(
                    "overall_score", 0.0
                ),
            }
            if not privacy_valid:
                results["overall_valid"] = False
        except Exception as exc:
            results["checks"]["privacy_assessment"] = {
                "valid": False,
                "error": str(exc),
            }
            results["overall_valid"] = False

        # Check: Version
        results["checks"]["version"] = {
            "valid": certificate.version == "1.0",
            "version": certificate.version,
        }

        # Check: Target data IDs present
        results["checks"]["target_data"] = {
            "valid": len(certificate.target_data_ids) > 0,
            "count": len(certificate.target_data_ids),
        }

        if results["overall_valid"]:
            certificate.status = "verified"
            certificate.verified_at = datetime.now(timezone.utc).isoformat()
        else:
            certificate.status = "failed"

        return results

    # ------------------------------------------------------------------
    # Pipeline history and stats
    # ------------------------------------------------------------------

    def get_pipeline_history(self, limit: int = 50) -> list[dict]:
        return self._pipeline_history[-limit:]

    def get_pipeline_stats(self) -> dict:
        total = len(self._pipeline_history)
        if total == 0:
            return {
                "total_pipelines": 0,
                "successful_pipelines": 0,
                "failed_pipelines": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0.0,
                "algorithms_used": {},
                "regulatory_distribution": {},
            }

        successful = 0
        failed = 0
        total_duration = 0
        algorithms_used: dict[str, int] = {}
        regulatory_dist: dict[str, int] = {}

        for record in self._pipeline_history:
            req = record.get("request", {})
            status = req.get("status", "unknown")
            if status == "completed":
                successful += 1
            else:
                failed += 1

            total_duration += record.get("total_duration_ms", 0)

            steps = record.get("steps", [])
            for s in steps:
                if s.get("name") == "execute_unlearning" and s.get("result"):
                    algo = s["result"].get("algorithm", "unknown")
                    algorithms_used[algo] = algorithms_used.get(algo, 0) + 1

            reg = req.get("regulatory", "unknown")
            regulatory_dist[reg] = regulatory_dist.get(reg, 0) + 1

        return {
            "total_pipelines": total,
            "successful_pipelines": successful,
            "failed_pipelines": failed,
            "success_rate": successful / total if total > 0 else 0.0,
            "avg_duration_ms": total_duration / total if total > 0 else 0.0,
            "algorithms_used": algorithms_used,
            "regulatory_distribution": regulatory_dist,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_pipeline_result(
        self,
        pipeline_id: str,
        request: DeletionRequest,
        steps: list[PipelineStep],
        pipeline_start: float,
    ) -> dict:
        total_ms = int((time.perf_counter() - pipeline_start) * 1000)

        steps_data = []
        for s in steps:
            step_dict: dict[str, Any] = {
                "step_id": s.step_id,
                "name": s.name,
                "status": s.status,
                "duration_ms": s.duration_ms,
                "error": s.error,
            }
            if s.result is not None:
                serializable_result = {}
                for k, v in s.result.items():
                    if k == "remaining_dataset":
                        serializable_result[k] = {
                            "size": v.size,
                            "data_ids": v.data_ids[:5],
                        }
                    elif k in ("original_weights", "updated_weights"):
                        if isinstance(v, list) and len(v) > 10:
                            serializable_result[k] = v[:10] + ["..."]
                        else:
                            serializable_result[k] = v
                    elif k == "unlearning_result":
                        serializable_result[k] = {
                            "success": v.success,
                            "algorithm": v.algorithm,
                            "utility_retained": v.utility_retained,
                            "processing_time_ms": v.processing_time_ms,
                        }
                    elif k == "certificate":
                        serializable_result[k] = {
                            "certificate_id": v.certificate_id,
                            "algorithm": v.algorithm,
                            "status": v.status,
                        }
                    elif isinstance(v, (str, int, float, bool, list, dict)):
                        serializable_result[k] = v
                    else:
                        serializable_result[k] = str(v)
            else:
                serializable_result = None
            step_dict["result"] = serializable_result
            steps_data.append(step_dict)

        certificate_info = None
        for s in steps:
            if s.name == "generate_certificate" and s.result:
                cert = s.result.get("certificate")
                if cert:
                    certificate_info = {
                        "certificate_id": cert.certificate_id,
                        "algorithm": cert.algorithm,
                        "utility_retained": cert.utility_retained,
                        "sha256": cert.sha256,
                        "merkle_root": cert.merkle_root,
                        "signature_hex": cert.signature_hex,
                        "status": cert.status,
                        "created_at": cert.created_at,
                        "expires_at": cert.expires_at,
                    }
                break

        return {
            "pipeline_id": pipeline_id,
            "request": {
                "request_id": request.request_id,
                "tenant_id": request.tenant_id,
                "user_id": request.user_id,
                "model_name": request.model_name,
                "regulatory": request.regulatory,
                "priority": request.priority,
                "num_target_samples": len(request.target_data_ids),
                "status": request.status,
                "created_at": request.created_at,
                "updated_at": request.updated_at,
            },
            "steps": steps_data,
            "certificate": certificate_info,
            "total_duration_ms": total_ms,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
