from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import (
    CurrentUser,
    DatabaseSession,
    TenantID,
    VerificationServiceDep,
    default_rate_limiter,
    require_permission,
)
from app.core.logging import get_logger
from app.core.rbac import Permission
from app.infrastructure.external.ml_engine import ml_engine_client, MLEngineClientError

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(default_rate_limiter)])


class ZKProofGenerateRequest(BaseModel):
    job_id: str
    request_id: str
    leaf_data: str
    all_leaves: list[str]
    hash_algorithm: str = "sha3_256"


@router.get("/proofs/{proof_id}")
async def get_proof(
    proof_id: str,
    current_user: Annotated[dict, Depends(require_permission(Permission.VERIFICATION_READ))],
    verification_service: VerificationServiceDep = ...,
):
    proof = await verification_service.get_proof(proof_id)
    return {
        "id": proof.id,
        "proof_type": proof.proof_type.value,
        "merkle_root": proof.merkle_root,
        "signature_hex": proof.signature_hex,
        "public_key_hex": proof.public_key_hex,
        "verified": proof.verified,
        "certificate": proof.certificate,
        "zk_proof": proof.zk_proof,
        "created_at": proof.created_at.isoformat() if proof.created_at else None,
        "expires_at": proof.expires_at.isoformat() if proof.expires_at else None,
    }


@router.post("/proofs/{proof_id}/verify")
async def verify_proof(
    proof_id: str,
    current_user: Annotated[dict, Depends(require_permission(Permission.VERIFICATION_VERIFY))],
    verification_service: VerificationServiceDep = ...,
):
    proof = await verification_service.get_proof(proof_id)
    verification = await verification_service.verify_proof(
        proof_id=proof_id,
        verifier_id=current_user.get("user_id"),
    )
    ml_verification_details = {}
    if proof.signature_hex and proof.public_key_hex:
        try:
            ml_result = await ml_engine_client.verify_proof(
                message=proof.merkle_root or "",
                signature_hex=proof.signature_hex,
                public_key_pem=proof.public_key_hex,
            )
            ml_verification_details = ml_result
            logger.info("ML engine proof verification for proof %s: %s", proof_id, ml_result)
        except MLEngineClientError as e:
            logger.warning("ML engine proof verification failed for proof %s: %s", proof_id, str(e))
            ml_verification_details = {"ml_engine_error": str(e)}
    details = verification.details if isinstance(verification.details, dict) else {"details": verification.details}
    details["ml_engine_verification"] = ml_verification_details
    return {
        "is_valid": verification.is_valid,
        "verification_details": details,
        "verified_at": verification.verified_at.isoformat() if verification.verified_at else None,
    }


@router.get("/proofs")
async def list_proofs(
    current_user: Annotated[dict, Depends(require_permission(Permission.VERIFICATION_READ))],
    verification_service: VerificationServiceDep = ...,
    tenant_id: TenantID = ...,
    request_id: Optional[str] = None,
    verified: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    if request_id:
        proof = await verification_service.get_proof(request_id)
        return {
            "data": [
                {
                    "id": proof.id,
                    "proof_type": proof.proof_type.value,
                    "merkle_root": proof.merkle_root,
                    "verified": proof.verified,
                    "created_at": proof.created_at.isoformat() if proof.created_at else None,
                }
            ],
            "meta": {"page": 1, "page_size": 1, "total": 1},
        }

    results, total = await verification_service.list_proofs(
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        verified=verified,
    )
    return {
        "data": [
            {
                "id": p.id,
                "proof_type": p.proof_type.value,
                "merkle_root": p.merkle_root,
                "verified": p.verified,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in results
        ],
        "meta": {"page": page, "page_size": page_size, "total": total},
    }


@router.get("/certificates/{certificate_hash}")
async def get_certificate(
    certificate_hash: str,
    current_user: Annotated[dict, Depends(require_permission(Permission.VERIFICATION_READ))],
    verification_service: VerificationServiceDep = ...,
):
    certificate = await verification_service.get_certificate(certificate_hash)
    if certificate is None:
        try:
            ml_cert = await ml_engine_client.generate_certificate(
                target_data_ids=[certificate_hash],
                model_name="",
                data_size=0,
                regulatory="gdpr",
            )
            return {"certificate": ml_cert}
        except MLEngineClientError as e:
            logger.warning("ML engine certificate generation failed for hash %s: %s", certificate_hash, str(e))
            return {"certificate": None}
    return {"certificate": certificate}


@router.post("/proofs/generate-zksnark", status_code=status.HTTP_201_CREATED)
async def generate_zksnark_proof(
    body: ZKProofGenerateRequest,
    current_user: Annotated[dict, Depends(require_permission(Permission.VERIFICATION_VERIFY))] = ...,
    verification_service: VerificationServiceDep = ...,
    tenant_id: TenantID = ...,
):
    ml_proof_result = None
    try:
        ml_proof_result = await ml_engine_client.generate_zksnark_proof(
            leaf_data=body.leaf_data,
            all_leaves=body.all_leaves,
            hash_algorithm=body.hash_algorithm,
        )
        logger.info("ML engine zk-SNARK proof generated: %s", ml_proof_result)
    except MLEngineClientError as e:
        logger.warning("ML engine zk-SNARK proof generation failed: %s", str(e))

    proof = await verification_service.generate_zksnark_proof(
        tenant_id=tenant_id,
        job_id=body.job_id,
        request_id=body.request_id,
        leaf_data=body.leaf_data,
        all_leaves=body.all_leaves,
        hash_algorithm=body.hash_algorithm,
        actor_id=current_user.get("user_id"),
    )
    return {
        "id": proof.id,
        "proof_type": proof.proof_type.value,
        "merkle_root": proof.merkle_root,
        "zk_proof": proof.zk_proof,
        "verified": proof.verified,
        "ml_proof": ml_proof_result,
        "created_at": proof.created_at.isoformat() if proof.created_at else None,
    }


@router.post("/proofs/generate", status_code=status.HTTP_201_CREATED)
async def generate_proof(
    job_id: str = Query(...),
    request_id: str = Query(...),
    deletion_steps: list[str] = Query(...),
    algorithm: str = "ed25519",
    current_user: Annotated[dict, Depends(require_permission(Permission.VERIFICATION_VERIFY))] = ...,
    verification_service: VerificationServiceDep = ...,
    tenant_id: TenantID = ...,
):
    ml_proof_result = None
    try:
        ml_proof_result = await ml_engine_client.generate_proof(
            deletion_steps=deletion_steps,
            algorithm=algorithm,
        )
        logger.info("ML engine proof generated: %s", ml_proof_result)
    except MLEngineClientError as e:
        logger.warning("ML engine proof generation failed: %s", str(e))

    proof = await verification_service.generate_proof(
        tenant_id=tenant_id,
        job_id=job_id,
        request_id=request_id,
        deletion_steps=deletion_steps,
        algorithm=algorithm,
        actor_id=current_user.get("user_id"),
    )
    return {
        "id": proof.id,
        "proof_type": proof.proof_type.value,
        "merkle_root": proof.merkle_root,
        "merkle_tree_depth": proof.merkle_tree_depth,
        "signature_hex": proof.signature_hex,
        "public_key_hex": proof.public_key_hex,
        "verified": proof.verified,
        "ml_proof": ml_proof_result,
        "created_at": proof.created_at.isoformat() if proof.created_at else None,
    }
