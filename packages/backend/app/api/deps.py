import hashlib
import hmac
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.rate_limiter import default_rate_limiter  # noqa: F401 (re-exported for API routers)
from app.core.rbac import Permission, check_permission
from app.core.security import TokenError, token_manager
from app.domain.audit.entities import ActorType, EventStatus, EventType
from app.domain.audit.services import AuditService
from app.domain.auth.entities import UserRole
from app.domain.auth.services import AuthService
from app.domain.chat.services import ChatService
from app.domain.compliance.services import TenantService
from app.domain.memory.services import MemoryService
from app.domain.unlearning.services import UnlearningService
from app.domain.verification.services import VerificationService
from app.infrastructure.database.repositories.audit import SQLAlchemyAuditEventRepository
from app.infrastructure.database.repositories.auth import (
    SQLAlchemyApiKeyRepository,
    SQLAlchemySessionRepository,
    SQLAlchemyTenantRepository,
    SQLAlchemyUserRepository,
)
from app.infrastructure.database.repositories.chat import (
    SQLAlchemyChatFolderRepository,
    SQLAlchemyChatSessionRepository,
    SQLAlchemyMessageRepository,
)
from app.infrastructure.database.repositories.compliance import (
    SQLAlchemyWebhookEventLogRepository,
    SQLAlchemyWebhookRepository,
)
from app.infrastructure.database.repositories.memory import SQLAlchemyMemoryRepository
from app.infrastructure.database.repositories.unlearning import (
    SQLAlchemyDeletionQueueRepository,
    SQLAlchemyModelVersionRepository,
    SQLAlchemyUnlearningJobRepository,
    SQLAlchemyUnlearningRequestRepository,
)
from app.infrastructure.database.repositories.verification import (
    SQLAlchemyDeletionProofRepository,
    SQLAlchemyProofVerificationRepository,
)

logger = get_logger(__name__)

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)] = None,
    session: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> dict[str, Any]:
    token = None
    if credentials:
        token = credentials.credentials
    else:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if token:
        try:
            payload = token_manager.verify_token(token, expected_type="access")
            jti = payload.get("jti")
            if jti and await cache.exists(f"jti:blacklist:{jti}"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return {
                "user_id": payload.get("sub"),
                "tenant_id": payload.get("tenant_id"),
                "role": payload.get("role"),
                "email": payload.get("email"),
                "jti": jti,
                "auth_type": "jwt",
                "mfa_verified": payload.get("mfa_verified", False),
            }
        except TokenError:
            logger.debug("JWT token verification failed, falling through to API key auth")

    api_key = request.headers.get("X-API-Key")
    if api_key:
        api_key_repo = SQLAlchemyApiKeyRepository(session)
        key_hash = hmac.new(settings.secret_key.encode(), api_key.encode(), hashlib.sha384).hexdigest()
        key_record = await api_key_repo.get_by_key_hash(key_hash)
        if key_record and key_record.is_active:
            await api_key_repo.update_last_used(key_record.id)
            creator_role = UserRole.MEMBER.value
            if key_record.created_by:
                user_repo = SQLAlchemyUserRepository(session)
                creator = await user_repo.get_by_id(key_record.created_by)
                if creator:
                    creator_role = creator.role.value
            return {
                "user_id": key_record.created_by,
                "tenant_id": key_record.tenant_id,
                "role": creator_role,
                "email": None,
                "jti": None,
                "auth_type": "api_key",
                "api_key_id": key_record.id,
                "api_key_name": key_record.name,
                "scopes": key_record.scopes,
            }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_optional_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)] = None,
) -> dict[str, Any] | None:
    try:
        return await get_current_user(request, credentials)
    except HTTPException:
        return None


def require_role(role: str):
    async def role_checker(
        current_user: Annotated[dict, Depends(get_current_user)],
    ) -> dict:
        user_role = current_user.get("role", "member")
        role_hierarchy = {"admin": 4, "compliance_officer": 3, "unlearning_auditor": 2, "member": 1, "viewer": 0}
        required_level = role_hierarchy.get(role, 0)
        user_level = role_hierarchy.get(user_role, 0)
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {role} role or higher",
            )
        return current_user
    return role_checker


async def get_tenant_id(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> str:
    return current_user["tenant_id"]


async def get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


async def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AuthService:
    audit_repo = SQLAlchemyAuditEventRepository(session)
    audit_service = AuditService(repo=audit_repo)
    return AuthService(
        user_repo=SQLAlchemyUserRepository(session),
        session_repo=SQLAlchemySessionRepository(session),
        tenant_repo=SQLAlchemyTenantRepository(session),
        audit_service=audit_service,
    )


async def get_audit_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AuditService:
    return AuditService(repo=SQLAlchemyAuditEventRepository(session))


def require_permission(permission: Permission):
    async def permission_checker(
        current_user: Annotated[dict, Depends(get_current_user)],
        session: Annotated[AsyncSession, Depends(get_db)],
    ) -> dict:
        role = current_user.get("role", "member")
        if not check_permission(role, permission):
            audit_repo = SQLAlchemyAuditEventRepository(session)
            audit_svc = AuditService(repo=audit_repo)
            await audit_svc.record(
                tenant_id=current_user.get("tenant_id", ""),
                event_type=EventType.SECURITY_ASSESSMENT,
                actor_id=current_user.get("user_id"),
                actor_type=ActorType.USER,
                action="rbac.permission_denied",
                status=EventStatus.FAILURE,
                metadata={"permission": permission.value, "role": role},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission.value}",
            )
        return current_user
    return permission_checker


async def require_mfa(
    current_user: Annotated[dict, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    user_id = current_user.get("user_id")
    if not user_id:
        return
    repo = SQLAlchemyUserRepository(session)
    user = await repo.get_by_id(user_id)
    if user and user.mfa_enabled:
        if not current_user.get("mfa_verified"):
            audit_repo = SQLAlchemyAuditEventRepository(session)
            audit_svc = AuditService(repo=audit_repo)
            await audit_svc.record(
                tenant_id=current_user.get("tenant_id", ""),
                event_type=EventType.SECURITY_ASSESSMENT,
                actor_id=user_id,
                actor_type=ActorType.USER,
                action="mfa.enforcement.blocked",
                status=EventStatus.FAILURE,
                metadata={"reason": "MFA_VERIFIED_REQUIRED"},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="MFA is enabled. Complete MFA verification to perform this action.",
            )


async def get_unlearning_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> UnlearningService:
    return UnlearningService(
        request_repo=SQLAlchemyUnlearningRequestRepository(session),
        job_repo=SQLAlchemyUnlearningJobRepository(session),
        deletion_queue_repo=SQLAlchemyDeletionQueueRepository(session),
        model_version_repo=SQLAlchemyModelVersionRepository(session),
        audit_service=audit_service,
    )


async def get_verification_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> VerificationService:
    return VerificationService(
        proof_repo=SQLAlchemyDeletionProofRepository(session),
        verification_repo=SQLAlchemyProofVerificationRepository(session),
        audit_service=audit_service,
    )


async def get_memory_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> MemoryService:
    return MemoryService(repo=SQLAlchemyMemoryRepository(session))


async def get_chat_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ChatService:
    return ChatService(
        session_repo=SQLAlchemyChatSessionRepository(session),
        message_repo=SQLAlchemyMessageRepository(session),
        folder_repo=SQLAlchemyChatFolderRepository(session),
    )


async def get_tenant_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> TenantService:
    return TenantService(
        tenant_repo=SQLAlchemyTenantRepository(session),
        webhook_repo=SQLAlchemyWebhookRepository(session),
        webhook_log_repo=SQLAlchemyWebhookEventLogRepository(session),
        audit_service=audit_service,
    )


CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]
OptionalCurrentUser = Annotated[dict[str, Any] | None, Depends(get_optional_current_user)]
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]
TenantID = Annotated[str, Depends(get_tenant_id)]
RequestID = Annotated[str | None, Depends(get_request_id)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
MemoryServiceDep = Annotated[MemoryService, Depends(get_memory_service)]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
UnlearningServiceDep = Annotated[UnlearningService, Depends(get_unlearning_service)]
VerificationServiceDep = Annotated[VerificationService, Depends(get_verification_service)]
TenantServiceDep = Annotated[TenantService, Depends(get_tenant_service)]
