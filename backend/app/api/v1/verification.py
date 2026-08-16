from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.repositories.certificate_repo import CertificateRepository
from app.schemas.certificate import VerificationOut
from app.services.certificate import CertificateService

router = APIRouter(prefix="/verification", tags=["verification"])


@router.post("/verify/{certificate_id}", response_model=VerificationOut)
async def verify_certificate(certificate_id: str, db: DbSession, user: CurrentUser) -> VerificationOut:
    """Independently verify a deletion certificate."""
    cert = await CertificateRepository(db).get(certificate_id)
    result = await CertificateService(db).verify(cert)
    return VerificationOut(**result)
