from fastapi import APIRouter

from app.api.v1 import (
    admin,
    attacks,
    auth,
    benchmarks,
    certificates,
    compliance,
    datasets,
    models,
    privacy,
    unlearning,
    verification,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(datasets.router)
api_router.include_router(models.router)
api_router.include_router(privacy.router)
api_router.include_router(unlearning.router)
api_router.include_router(certificates.router)
api_router.include_router(verification.router)
api_router.include_router(compliance.router)
api_router.include_router(attacks.router)
api_router.include_router(benchmarks.router)
api_router.include_router(admin.router)
