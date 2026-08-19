"""Admin portal service (Phase 7).

User management (create, deactivate, role assignment), the RBAC role /
permission matrix, deployment-log recording, and a platform overview combining
counts from the operational tables.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationFailedError
from app.core.rbac import VALID_ROLES, permission_definitions, role_permissions
from app.core.security import hash_password
from app.db.models import (
    APIKey,
    Certificate,
    Dataset,
    DeletionRequest,
    DeploymentLog,
    MLModel,
    Notification,
    User,
    VerificationReport,
)
from app.repositories.user_repo import UserRepository


class AdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    # ------------------------------------------------------------------ users

    async def create_user(
        self,
        *,
        email: str,
        full_name: str,
        password: str,
        role: str = "viewer",
        is_active: bool = True,
    ) -> User:
        if role not in VALID_ROLES:
            raise ValidationFailedError(f"role must be one of {VALID_ROLES}")
        user = await self.users.create(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            role=role,
        )
        user.is_active = is_active
        await self.session.flush()
        return user

    async def set_role(self, user_id: str, role: str) -> User:
        if role not in VALID_ROLES:
            raise ValidationFailedError(f"role must be one of {VALID_ROLES}")
        user = await self.users.get(user_id)
        user.role = role
        await self.session.flush()
        return user

    async def set_active(self, user_id: str, is_active: bool) -> User:
        user = await self.users.get(user_id)
        user.is_active = is_active
        await self.session.flush()
        return user

    async def list_users(self, *, limit: int = 500) -> list[dict[str, Any]]:
        users = await self.users.list(limit=limit)
        return [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "is_active": u.is_active,
                "permissions": role_permissions(u.role),
            }
            for u in users
        ]

    # ------------------------------------------------------------------- rbac

    async def rbac_matrix(self) -> dict[str, Any]:
        all_permissions: set[str] = set()
        for role in VALID_ROLES:
            all_permissions.update(role_permissions(role))
        return {
            "roles": VALID_ROLES,
            "matrix": permission_definitions(),
            "permissions": sorted(all_permissions),
        }

    # -------------------------------------------------------------- deployment

    async def record_deployment(
        self,
        *,
        version: str,
        environment: str = "staging",
        status: str = "pending",
        commit_sha: str | None = None,
        artifact: str | None = None,
        deployed_by: str | None = None,
        log: str | None = None,
    ) -> DeploymentLog:
        entry = DeploymentLog(
            version=version,
            environment=environment,
            status=status,
            commit_sha=commit_sha,
            artifact=artifact,
            deployed_by=deployed_by,
            log=log,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def deployment_history(self, *, limit: int = 50) -> list[dict[str, Any]]:
        result = await self.session.execute(
            select(DeploymentLog).order_by(DeploymentLog.created_at.desc()).limit(limit)
        )
        rows = list(result.scalars().all())
        return [
            {
                "id": r.id,
                "version": r.version,
                "environment": r.environment,
                "status": r.status,
                "commit_sha": r.commit_sha,
                "artifact": r.artifact,
                "deployed_by": r.deployed_by,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

    # --------------------------------------------------------------- overview

    async def overview(self) -> dict[str, Any]:
        counts = {
            "users": await self.session.scalar(select(func.count()).select_from(User)) or 0,
            "datasets": await self.session.scalar(select(func.count()).select_from(Dataset)) or 0,
            "models": await self.session.scalar(select(func.count()).select_from(MLModel)) or 0,
            "deletion_requests": await self.session.scalar(select(func.count()).select_from(DeletionRequest)) or 0,
            "certificates": await self.session.scalar(select(func.count()).select_from(Certificate)) or 0,
            "verification_reports": await self.session.scalar(select(func.count()).select_from(VerificationReport)) or 0,
            "api_keys": await self.session.scalar(select(func.count()).select_from(APIKey)) or 0,
            "notifications": await self.session.scalar(select(func.count()).select_from(Notification)) or 0,
        }
        return {"counts": counts}
