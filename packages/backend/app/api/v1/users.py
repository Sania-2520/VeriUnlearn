from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import (
    CurrentUser,
    default_rate_limiter,
    get_auth_service,
    require_mfa,
    require_permission,
)
from app.core.rbac import Permission
from app.domain.auth.services import AuthService

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]

router = APIRouter(dependencies=[Depends(default_rate_limiter), Depends(require_permission(Permission.USERS_READ))])


class ProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    avatar_url: str | None = None
    role: str
    is_email_verified: bool
    is_active: bool
    preferences: dict[str, Any]


class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    avatar_url: str | None = None
    preferences: dict[str, Any] | None = None


class SessionResponse(BaseModel):
    id: str
    user_agent: str | None = None
    ip_address: str | None = None
    device_name: str | None = None
    created_at: datetime
    expires_at: datetime
    is_current: bool = False


@router.get("/me")
async def get_me(
    current_user: CurrentUser,
    auth: AuthServiceDep,
):
    user = await auth.get_profile(current_user["user_id"])
    return ProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        role=user.role.value,
        is_email_verified=user.is_email_verified,
        is_active=user.is_active,
        preferences=user.preferences,
    )


@router.patch("/me")
async def update_me(
    request: UpdateProfileRequest,
    current_user: CurrentUser,
    auth: AuthServiceDep,
):
    user = await auth.update_profile(
        user_id=current_user["user_id"],
        full_name=request.full_name,
        avatar_url=request.avatar_url,
        preferences=request.preferences,
    )
    return ProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        role=user.role.value,
        is_email_verified=user.is_email_verified,
        is_active=user.is_active,
        preferences=user.preferences,
    )


@router.get("/me/sessions")
async def get_sessions(
    current_user: CurrentUser,
    auth: AuthServiceDep,
):
    sessions = await auth.get_sessions(current_user["user_id"])
    current_jti = current_user.get("jti")
    return {
        "data": [
            SessionResponse(
                id=s.id,
                user_agent=s.user_agent,
                ip_address=s.ip_address,
                device_name=s.device_name,
                created_at=s.created_at,
                expires_at=s.expires_at,
                is_current=s.access_token_jti == current_jti,
            )
            for s in sessions
        ]
    }


@router.delete("/me/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: CurrentUser,
    auth: AuthServiceDep,
    _mfa: Annotated[None, Depends(require_mfa)] = None,
):
    await auth.revoke_session(current_user["user_id"], session_id)
    return {"message": "Session revoked"}


@router.delete("/me/sessions")
async def revoke_all_sessions(
    current_user: CurrentUser,
    auth: AuthServiceDep,
    _mfa: Annotated[None, Depends(require_mfa)] = None,
):
    await auth.revoke_all_sessions(current_user["user_id"])
    return {"message": "All sessions revoked"}
