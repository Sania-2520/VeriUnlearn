from __future__ import annotations

from sqlalchemy import select

from app.db.models import CryptoProof, VerificationReport
from app.repositories.base import BaseRepository


class VerificationReportRepository(BaseRepository[VerificationReport]):
    model = VerificationReport

    async def create(self, report: VerificationReport) -> VerificationReport:
        return await self.add(report)

    async def get_by_certificate(self, certificate_id: str) -> list[VerificationReport]:
        result = await self.session.execute(
            select(VerificationReport)
            .where(VerificationReport.certificate_id == certificate_id)
            .order_by(VerificationReport.created_at.desc())
        )
        return list(result.scalars().all())


class CryptoProofRepository(BaseRepository[CryptoProof]):
    model = CryptoProof

    async def create(self, proof: CryptoProof) -> CryptoProof:
        return await self.add(proof)

    async def get_by_proof_id(self, proof_id: str) -> CryptoProof | None:
        result = await self.session.execute(
            select(CryptoProof).where(CryptoProof.proof_id == proof_id)
        )
        return result.scalar_one_or_none()

    async def list_by_subject(self, subject_id: str, limit: int = 50) -> list[CryptoProof]:
        result = await self.session.execute(
            select(CryptoProof)
            .where(CryptoProof.subject_id == subject_id)
            .order_by(CryptoProof.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
