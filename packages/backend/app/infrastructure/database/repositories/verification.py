from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.verification.entities import (
    DeletionProof as DeletionProofEntity,
    ProofVerification as ProofVerificationEntity,
    ProofType,
)
from app.domain.verification.interfaces import DeletionProofRepository, ProofVerificationRepository
from app.infrastructure.database.models import DeletionProofModel, ProofVerificationModel


class SQLAlchemyDeletionProofRepository(DeletionProofRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, proof: DeletionProofEntity) -> DeletionProofEntity:
        model = DeletionProofModel(
            id=proof.id,
            tenant_id=proof.tenant_id,
            job_id=proof.job_id,
            request_id=proof.request_id,
            proof_type=proof.proof_type.value if isinstance(proof.proof_type, ProofType) else proof.proof_type,
            merkle_root=proof.merkle_root,
            merkle_tree_depth=proof.merkle_tree_depth,
            merkle_tree=proof.merkle_tree,
            signature_algorithm=proof.signature_algorithm,
            signature_hex=proof.signature_hex,
            public_key_hex=proof.public_key_hex,
            zk_proof=proof.zk_proof,
            certificate=proof.certificate,
            certificate_hash=proof.certificate_hash,
            verified=proof.verified,
            verified_at=proof.verified_at,
            metadata=proof.metadata,
            expires_at=proof.expires_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def get_by_id(self, proof_id: str) -> Optional[DeletionProofEntity]:
        result = await self._session.execute(
            select(DeletionProofModel).where(DeletionProofModel.id == proof_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_request(self, request_id: str) -> Optional[DeletionProofEntity]:
        result = await self._session.execute(
            select(DeletionProofModel).where(DeletionProofModel.request_id == request_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_tenant(
        self, tenant_id: str, page: int, page_size: int,
        verified: Optional[bool] = None,
    ) -> tuple[list[DeletionProofEntity], int]:
        query = select(DeletionProofModel).where(DeletionProofModel.tenant_id == tenant_id)
        count_query = select(func.count(DeletionProofModel.id)).where(DeletionProofModel.tenant_id == tenant_id)

        if verified is not None:
            query = query.where(DeletionProofModel.verified == verified)
            count_query = count_query.where(DeletionProofModel.verified == verified)

        count_result = await self._session.execute(count_query)
        total = count_result.scalar() or 0

        offset = (page - 1) * page_size
        query = query.order_by(desc(DeletionProofModel.created_at)).offset(offset).limit(page_size)
        result = await self._session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(m) for m in models], total

    async def update(self, proof: DeletionProofEntity) -> DeletionProofEntity:
        await self._session.execute(
            __import__("sqlalchemy").update(DeletionProofModel)
            .where(DeletionProofModel.id == proof.id)
            .values(
                verified=proof.verified,
                verified_at=proof.verified_at or datetime.now(timezone.utc),
                certificate=proof.certificate,
                certificate_hash=proof.certificate_hash,
            event_metadata=proof.metadata,
            )
        )
        return proof

    @staticmethod
    def _to_entity(model: DeletionProofModel) -> DeletionProofEntity:
        return DeletionProofEntity(
            id=model.id,
            tenant_id=model.tenant_id,
            job_id=model.job_id,
            request_id=model.request_id,
            proof_type=ProofType(model.proof_type) if model.proof_type else ProofType.MERKLE,
            merkle_root=model.merkle_root or "",
            merkle_tree_depth=model.merkle_tree_depth or 0,
            merkle_tree=model.merkle_tree or {},
            signature_algorithm=model.signature_algorithm or "ed25519",
            signature_hex=model.signature_hex or "",
            public_key_hex=model.public_key_hex or "",
            zk_proof=model.zk_proof,
            certificate=model.certificate,
            certificate_hash=model.certificate_hash,
            verified=model.verified,
            verified_at=model.verified_at,
            metadata=model.event_metadata or {},
            created_at=model.created_at,
            expires_at=model.expires_at,
        )


class SQLAlchemyProofVerificationRepository(ProofVerificationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, verification: ProofVerificationEntity) -> ProofVerificationEntity:
        model = ProofVerificationModel(
            id=verification.id,
            proof_id=verification.proof_id,
            verifier_id=verification.verifier_id,
            verification_method=verification.verification_method,
            is_valid=verification.is_valid,
            details=verification.details,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def get_by_proof(self, proof_id: str) -> Optional[ProofVerificationEntity]:
        result = await self._session.execute(
            select(ProofVerificationModel).where(ProofVerificationModel.proof_id == proof_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_proof(self, proof_id: str) -> list[ProofVerificationEntity]:
        result = await self._session.execute(
            select(ProofVerificationModel)
            .where(ProofVerificationModel.proof_id == proof_id)
            .order_by(desc(ProofVerificationModel.verified_at))
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    @staticmethod
    def _to_entity(model: ProofVerificationModel) -> ProofVerificationEntity:
        return ProofVerificationEntity(
            id=model.id,
            proof_id=model.proof_id,
            verifier_id=model.verifier_id,
            verification_method=model.verification_method,
            is_valid=model.is_valid,
            details=model.details or {},
            verified_at=model.verified_at,
        )
