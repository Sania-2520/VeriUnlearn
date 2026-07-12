from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from pathlib import Path

from app.core.dependencies import DatabaseDep, CurrentUser
from app.schemas.unlearning import (
    UnlearningBenchmarkRequest,
    UnlearningBenchmarkResponse,
    ProofVerificationResponse,
    UnlearningRequestCreate,
    UnlearningRequestResponse,
    UnlearningResultResponse,
)
from app.services.unlearning_benchmark_service import UnlearningBenchmarkService
from app.services.unlearning_service import UnlearningService
from app.services.proof_verification_service import ProofVerificationService

router = APIRouter(prefix="/unlearning", tags=["Unlearning"])


@router.post("/benchmark", response_model=UnlearningBenchmarkResponse)
async def benchmark_algorithms(body: UnlearningBenchmarkRequest, user: CurrentUser):
    service = UnlearningBenchmarkService()
    return service.compare(
        dataset_size=body.dataset_size,
        num_deleted=body.num_deleted,
        sensitivity=body.sensitivity,
        latency_budget=body.latency_budget,
    )


@router.post("/requests", response_model=UnlearningRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_unlearning_request(body: UnlearningRequestCreate, user: CurrentUser, db: DatabaseDep):
    service = UnlearningService(db)
    request = await service.create_request(
        user=user,
        sample_ids=body.sample_ids,
        algorithm=body.algorithm,
        reason=body.reason,
    )
    return request


@router.get("/requests", response_model=list[UnlearningRequestResponse])
async def list_requests(user: CurrentUser, db: DatabaseDep):
    service = UnlearningService(db)
    if user.role == "admin":
        requests = await service.get_requests()
    else:
        requests = await service.get_requests(user_id=user.id)
    return requests


@router.get("/requests/{request_id}", response_model=UnlearningRequestResponse)
async def get_request(request_id: int, user: CurrentUser, db: DatabaseDep):
    service = UnlearningService(db)
    requests = await service.get_requests()
    req = next((r for r in requests if r.id == request_id), None)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    return req


@router.post("/requests/{request_id}/execute")
async def execute_unlearning(request_id: int, user: CurrentUser, db: DatabaseDep):
    service = UnlearningService(db)
    try:
        result = await service.execute_unlearning(request_id)
        return {"status": "completed", "result_id": result.id}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/results/{request_id}", response_model=UnlearningResultResponse)
async def get_result(request_id: int, user: CurrentUser, db: DatabaseDep):
    service = UnlearningService(db)
    result = await service.get_result(request_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")
    return result


@router.get("/results/{request_id}/verify", response_model=ProofVerificationResponse)
async def verify_result(request_id: int, user: CurrentUser, db: DatabaseDep):
    service = UnlearningService(db)
    result = await service.get_result(request_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")
    verifier = ProofVerificationService()
    return verifier.verify_result(result)


@router.get("/results/{request_id}/certificate")
async def download_certificate(request_id: int, user: CurrentUser, db: DatabaseDep):
    service = UnlearningService(db)
    result = await service.get_result(request_id)
    if result is None or not result.certificate_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")
    certificate_path = Path(result.certificate_path)
    if not certificate_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate file missing")
    return FileResponse(certificate_path, media_type="application/json", filename=certificate_path.name)
