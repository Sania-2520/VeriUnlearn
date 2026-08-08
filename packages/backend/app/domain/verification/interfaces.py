from abc import ABC, abstractmethod
from typing import Optional

from app.domain.verification.entities import DeletionProof, ProofVerification


class DeletionProofRepository(ABC):
    @abstractmethod
    async def create(self, proof: DeletionProof) -> DeletionProof:
        ...

    @abstractmethod
    async def get_by_id(self, proof_id: str) -> Optional[DeletionProof]:
        ...

    @abstractmethod
    async def get_by_request(self, request_id: str) -> Optional[DeletionProof]:
        ...

    @abstractmethod
    async def get_by_certificate_hash(self, certificate_hash: str) -> Optional[DeletionProof]:
        ...

    @abstractmethod
    async def list_by_tenant(
        self, tenant_id: str, page: int, page_size: int,
        verified: Optional[bool] = None,
    ) -> tuple[list[DeletionProof], int]:
        ...

    @abstractmethod
    async def update(self, proof: DeletionProof) -> DeletionProof:
        ...


class ProofVerificationRepository(ABC):
    @abstractmethod
    async def create(self, verification: ProofVerification) -> ProofVerification:
        ...

    @abstractmethod
    async def get_by_proof(self, proof_id: str) -> Optional[ProofVerification]:
        ...

    @abstractmethod
    async def list_by_proof(self, proof_id: str) -> list[ProofVerification]:
        ...
