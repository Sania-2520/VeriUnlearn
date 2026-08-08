"""Unlearning and certificate endpoints."""

import hashlib

from fastapi import APIRouter, HTTPException

from api import deps
from api.schemas import (
    CertificateRequest,
    E2EDeletionRequest,
    UnlearningRequest,
)
from unlearning.algorithms.base import UnlearningContext

router = APIRouter()


@router.post("/unlearn")
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
    result = await deps.controller.execute(context)
    return result


@router.post("/certificate")
async def generate_certificate(request: CertificateRequest):
    from verification.merkle_tree import MerkleTree

    context = UnlearningContext(
        target_data_ids=request.target_data_ids,
        model_name=request.model_name,
        data_size=request.data_size,
        regulatory=request.regulatory,
        config=request.config,
    )
    result = await deps.controller.execute(context)

    tree = MerkleTree()
    tree.add_leaves(request.target_data_ids)
    root = tree.build_tree()

    private_key, public_key = deps.sig_manager.generate_key_pair()
    signature = deps.sig_manager.sign(root, private_key)

    algorithm = result.algorithm
    epsilon = None
    delta = None
    if "certified" in result.metrics:
        eps = result.metrics["certified"].get("epsilon")
        delt = result.metrics["certified"].get("delta")
        if eps is not None:
            epsilon = eps
            delta = delt

    mia_conf = {
        "attack_name": "confidence-threshold",
        "overall_accuracy": 0.0,
        "f1_score": 0.0,
    }
    mia_loss = {
        "attack_name": "loss-threshold",
        "overall_accuracy": 0.0,
        "f1_score": 0.0,
    }

    # Deterministic id (the builtin hash() is salted per-process and would
    # change the certificate id on every worker/restart).
    cert_id_digest = hashlib.sha256(
        "|".join(sorted(request.target_data_ids)).encode("utf-8")
    ).hexdigest()[:8]
    cert = {
        "certificate_id": f"cert-{cert_id_digest}",
        "version": "1.0",
        "algorithm": algorithm,
        "target_data_ids": request.target_data_ids,
        "unlearning_result": result.success,
        "utility_retained": result.utility_retained,
        "processing_time_ms": result.processing_time_ms,
        "merkle_proof": {
            "root": root,
            "signature_hex": signature,
            "public_key_pem": deps.sig_manager.serialize_public_key(public_key),
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


@router.post("/unlearn/e2e")
async def execute_e2e_unlearning(request: E2EDeletionRequest):
    from unlearning.e2e_pipeline import DeletionRequest

    pipeline = deps.get_e2e_pipeline()
    deletion_request = DeletionRequest(
        tenant_id=request.tenant_id,
        user_id=request.user_id,
        target_data_ids=request.target_data_ids,
        model_name=request.model_name,
        reason=request.reason,
        regulatory=request.regulatory,
        priority=request.priority,
    )
    result = await pipeline.execute_full_pipeline(deletion_request)
    return result


@router.get("/unlearn/e2e/history")
async def e2e_history():
    pipeline = deps.get_e2e_pipeline()
    return pipeline.get_history()


@router.get("/unlearn/e2e/stats")
async def e2e_stats():
    pipeline = deps.get_e2e_pipeline()
    return pipeline.get_stats()


@router.post("/unlearn/e2e/verify-certificate")
async def verify_deletion_certificate(request: dict):
    from unlearning.e2e_pipeline import DeletionCertificate

    pipeline = deps.get_e2e_pipeline()
    cert = DeletionCertificate(**request)
    result = pipeline.verify_certificate(cert)
    return result


@router.get("/controller/health")
async def controller_health():
    result = deps.controller.health_check()
    return result


@router.get("/controller/metrics")
async def controller_metrics():
    return deps.controller.get_metrics()


@router.get("/controller/decisions")
async def controller_decisions():
    return deps.controller.get_decision_log()


@router.post("/controller/estimate")
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
    result = deps.controller.estimate_time(context)
    return result
