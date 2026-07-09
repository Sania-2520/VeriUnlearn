from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.users import router as users_router
from app.api.v1.providers import router as providers_router
from app.api.v1.rag import router as rag_router
from app.api.v1.memory import router as memory_router
from app.api.v1.unlearning import router as unlearning_router
from app.api.v1.verification import router as verification_router
from app.api.v1.security import router as security_router
from app.api.v1.audit import router as audit_router
from app.api.v1.compliance import router as compliance_router
from app.api.v1.admin import router as admin_router
from app.api.v1.api_keys import router as api_keys_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
router.include_router(api_keys_router, prefix="/auth/api-keys", tags=["API Keys"])
router.include_router(users_router, prefix="/users", tags=["Users"])
router.include_router(chat_router, prefix="/chat", tags=["Chat"])
router.include_router(providers_router, prefix="/providers", tags=["AI Providers"])
router.include_router(rag_router, prefix="/rag", tags=["RAG Engine"])
router.include_router(memory_router, prefix="/memory", tags=["Memory"])
router.include_router(unlearning_router, prefix="/unlearning", tags=["Unlearning"])
router.include_router(verification_router, prefix="/verify", tags=["Verification"])
router.include_router(security_router, prefix="/security", tags=["Security"])
router.include_router(audit_router, prefix="/audit", tags=["Audit"])
router.include_router(compliance_router, prefix="/compliance", tags=["Compliance"])
router.include_router(admin_router, prefix="/admin", tags=["Admin"])
