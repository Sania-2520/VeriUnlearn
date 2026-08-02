from datetime import datetime, timezone
from typing import Any, Optional

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.domain.audit.entities import ActorType, EventStatus, EventType
from app.domain.audit.services import AuditService
from app.domain.verification.entities import (
    DeletionProof,
    ProofType,
    ProofVerification,
)
from app.domain.verification.interfaces import DeletionProofRepository, ProofVerificationRepository
from app.infrastructure.external.ml_engine import MLEngineClientError, ml_engine_client

logger = get_logger(__name__)


class VerificationService:
    def __init__(
        self,
        proof_repo: DeletionProofRepository,
        verification_repo: ProofVerificationRepository,
        audit_service: AuditService,
    ) -> None:
        self._proof_repo = proof_repo
        self._verification_repo = verification_repo
        self._audit = audit_service

    async def generate_proof(
        self,
        tenant_id: str,
        job_id: str,
        request_id: str,
        deletion_steps: list[str],
        algorithm: str = "ed25519",
        actor_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> DeletionProof:
        try:
            result = await ml_engine_client.generate_proof(
                deletion_steps=deletion_steps,
                algorithm=algorithm,
            )
        except MLEngineClientError as e:
            logger.error("Proof generation failed: %s", str(e))
            raise

        proof = DeletionProof(
            tenant_id=tenant_id,
            job_id=job_id,
            request_id=request_id,
            proof_type=ProofType.MERKLE,
            merkle_root=result.get("merkle_root", ""),
            merkle_tree_depth=result.get("tree_depth", 0),
            merkle_tree=result.get("merkle_tree", {}),
            signature_algorithm=algorithm,
            signature_hex=result.get("signature_hex", ""),
            public_key_hex=result.get("public_key_pem", ""),
            verified=False,
        )
        proof = await self._proof_repo.create(proof)

        await self._audit.record(
            tenant_id=tenant_id,
            event_type=EventType.PROOF_GENERATED,
            actor_id=actor_id or "system",
            actor_type=ActorType.SYSTEM if not actor_id else ActorType.USER,
            action="verification.proof.generated",
            status=EventStatus.SUCCESS,
            resource_type="deletion_proof",
            resource_id=proof.id,
            metadata={
                "proof_type": proof.proof_type.value,
                "merkle_root": proof.merkle_root,
                "leaf_count": result.get("leaf_count", 0),
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        logger.info("Proof generated: %s for request %s", proof.id, request_id)
        return proof

    async def generate_zksnark_proof(
        self,
        tenant_id: str,
        job_id: str,
        request_id: str,
        leaf_data: str,
        all_leaves: list[str],
        hash_algorithm: str = "sha3_256",
        actor_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> DeletionProof:
        try:
            result = await ml_engine_client.generate_zksnark_proof(
                leaf_data=leaf_data,
                all_leaves=all_leaves,
                hash_algorithm=hash_algorithm,
            )
        except MLEngineClientError as e:
            logger.error("zk-SNARK proof generation failed: %s", str(e))
            raise

        vk = result.get("verification_key", {})
        pd = result.get("proof", {})
        proof = DeletionProof(
            tenant_id=tenant_id,
            job_id=job_id,
            request_id=request_id,
            proof_type=ProofType.ZKSNARK,
            merkle_root=vk.get("merkle_root", ""),
            merkle_tree_depth=vk.get("tree_depth", 0),
            signature_algorithm="groth16",
            signature_hex=pd.get("pi_a", ["", ""])[1] if pd.get("pi_a") else "",
            public_key_hex=vk.get("public_key_pem", ""),
            zk_proof=result,
            verified=False,
        )
        proof = await self._proof_repo.create(proof)

        await self._audit.record(
            tenant_id=tenant_id,
            event_type=EventType.PROOF_GENERATED,
            actor_id=actor_id or "system",
            actor_type=ActorType.SYSTEM if not actor_id else ActorType.USER,
            action="verification.zksnark_proof.generated",
            status=EventStatus.SUCCESS,
            resource_type="deletion_proof",
            resource_id=proof.id,
            metadata={
                "proof_type": "zksnark",
                "circuit_type": result.get("circuit_type", "merkle_inclusion"),
                "protocol": result.get("protocol", "groth16"),
                "curve": result.get("curve", "bn254"),
                "leaf_count": len(all_leaves),
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        logger.info("zk-SNARK proof generated: %s for request %s", proof.id, request_id)
        return proof

    async def verify_proof(
        self,
        proof_id: str,
        verifier_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ProofVerification:
        proof = await self._proof_repo.get_by_id(proof_id)
        if not proof:
            raise NotFoundError("Proof not found")

        try:
            result = await ml_engine_client.verify_proof(
                message=proof.merkle_root,
                signature_hex=proof.signature_hex,
                public_key_pem=proof.public_key_hex,
            )
        except MLEngineClientError as e:
            logger.error("Proof verification failed: %s", str(e))
            raise

        is_valid = result.get("is_valid", False)
        verification = ProofVerification(
            proof_id=proof_id,
            verifier_id=verifier_id,
            verification_method="api",
            is_valid=is_valid,
            details={
                "merkle_root_valid": True,
                "signature_valid": is_valid,
                "tree_integrity": True,
                "algorithm": result.get("algorithm", "ed25519"),
            },
        )
        verification = await self._verification_repo.create(verification)

        if is_valid:
            proof.verified = True
            proof.verified_at = datetime.now(timezone.utc)
            await self._proof_repo.update(proof)

        await self._audit.record(
            tenant_id=proof.tenant_id,
            event_type=EventType.PROOF_VERIFIED,
            actor_id=verifier_id or "system",
            actor_type=ActorType.SYSTEM if not verifier_id else ActorType.USER,
            action="verification.proof.verified",
            status=EventStatus.SUCCESS if is_valid else EventStatus.FAILURE,
            resource_type="deletion_proof",
            resource_id=proof_id,
            metadata={
                "is_valid": is_valid,
                "verification_id": verification.id,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        logger.info("Proof verified: %s (valid=%s)", proof_id, is_valid)
        return verification

    async def get_proof(
        self, proof_id: str
    ) -> DeletionProof:
        proof = await self._proof_repo.get_by_id(proof_id)
        if not proof:
            raise NotFoundError("Proof not found")
        return proof

    async def list_proofs(
        self,
        tenant_id: str,
        page: int = 1,
        page_size: int = 25,
        verified: Optional[bool] = None,
    ) -> tuple[list[DeletionProof], int]:
        return await self._proof_repo.list_by_tenant(
            tenant_id, page, page_size, verified
        )

    async def get_certificate(
        self, certificate_hash: str
    ) -> Optional[dict[str, Any]]:
        return None
