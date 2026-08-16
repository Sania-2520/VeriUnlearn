from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response

from app.api.deps import CurrentUser, DbSession
from app.api.serializers import certificate_out
from app.repositories.certificate_repo import CertificateRepository
from app.schemas.certificate import CertificateOut
from app.services.certificate import CertificateService

router = APIRouter(prefix="/certificates", tags=["certificates"])


@router.get("", response_model=list[CertificateOut])
async def list_certificates(db: DbSession, limit: int = 100) -> list[CertificateOut]:
    certs = await CertificateRepository(db).list(limit=limit)
    return [CertificateOut(**certificate_out(c)) for c in certs]


@router.get("/{certificate_id}", response_model=CertificateOut)
async def get_certificate(certificate_id: str, db: DbSession) -> CertificateOut:
    cert = await CertificateRepository(db).get(certificate_id)
    return CertificateOut(**certificate_out(cert))


@router.get("/{certificate_id}/download", response_class=JSONResponse)
async def download_certificate(certificate_id: str, db: DbSession) -> JSONResponse:
    cert = await CertificateRepository(db).get(certificate_id)
    return JSONResponse(
        content=cert.certificate_json,
        headers={"Content-Disposition": f'attachment; filename="certificate-{certificate_id}.json"'},
    )


@router.get("/{certificate_id}/pdf")
async def download_pdf(certificate_id: str, db: DbSession) -> Response:
    cert = await CertificateRepository(db).get(certificate_id)
    service = CertificateService(db)
    pdf_bytes = service.to_pdf_bytes(cert)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="certificate-{certificate_id}.pdf"'},
    )
