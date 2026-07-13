from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr

from app.api.deps import (
    CurrentUser,
    DatabaseSession,
    default_rate_limiter,
    get_auth_service,
    get_current_user,
    require_mfa,
    require_permission,
)
from app.core.rbac import Permission
from app.core.rate_limiter import make_rate_limiter, parse_rate_limit
from app.core.config import settings
from app.domain.auth.services import AuthService, MFARequiredError
from app.domain.auth.entities import UserRole
from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.infrastructure.external.oauth_service import oauth_service

_auth_count, _auth_window = parse_rate_limit(settings.rate_limit_auth)
_auth_rl = Depends(make_rate_limiter(
    max_requests=_auth_count,
    window_seconds=_auth_window,
    group="auth",
))
router = APIRouter(dependencies=[_auth_rl])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    tenant_slug: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None
    all_sessions: bool = False


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class VerifyEmailRequest(BaseModel):
    token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_email_verified: bool
    is_active: bool


class MFASetupResponse(BaseModel):
    secret: str
    provisioning_uri: str


class MFAEnableRequest(BaseModel):
    secret: str
    code: str


class MFASetupRequest(BaseModel):
    password: str


class MFADisableRequest(BaseModel):
    code: str


class MFAVerifyRequest(BaseModel):
    challenge_token: str
    code: str


class MFAChallengeResponse(BaseModel):
    mfa_required: bool = True
    challenge_token: str


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    auth: AuthServiceDep,
    req: Request,
):
    user, access_token, refresh_token = await auth.register(
        email=request.email,
        password=request.password,
        full_name=request.full_name,
        tenant_slug=request.tenant_slug,
        ip_address=req.client.host if req.client else None,
        user_agent=req.headers.get("user-agent"),
    )
    return {
        "user": UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            is_email_verified=user.is_email_verified,
            is_active=user.is_active,
        ),
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 900,
    }


@router.post("/login")
async def login(
    request: LoginRequest,
    auth: AuthServiceDep,
    req: Request,
):
    try:
        user, access_token, refresh_token = await auth.login(
            email=request.email,
            password=request.password,
            ip_address=req.client.host if req.client else None,
            user_agent=req.headers.get("user-agent"),
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )
    except MFARequiredError as e:
        return MFAChallengeResponse(challenge_token=e.challenge_token)


@router.post("/mfa/verify")
async def mfa_verify(
    request: MFAVerifyRequest,
    auth: AuthServiceDep,
):
    access_token, refresh_token = await auth.verify_mfa_challenge(
        challenge_token=request.challenge_token,
        totp_code=request.code,
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/mfa/totp/setup")
async def mfa_totp_setup(
    request: MFASetupRequest,
    current_user: CurrentUser,
    auth: AuthServiceDep,
):
    result = await auth.generate_totp_secret(
        user_id=current_user["user_id"],
        password=request.password,
    )
    return MFASetupResponse(**result)


@router.post("/mfa/totp/enable")
async def mfa_totp_enable(
    request: MFAEnableRequest,
    current_user: CurrentUser,
    auth: AuthServiceDep,
):
    await auth.enable_totp(
        user_id=current_user["user_id"],
        secret=request.secret,
        totp_code=request.code,
    )
    return {"message": "MFA enabled successfully"}


@router.post("/mfa/totp/disable")
async def mfa_totp_disable(
    request: MFADisableRequest,
    current_user: CurrentUser,
    auth: AuthServiceDep,
):
    await auth.disable_totp(
        user_id=current_user["user_id"],
        totp_code=request.code,
    )
    return {"message": "MFA disabled successfully"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: RefreshRequest,
    auth: AuthServiceDep,
):
    access_token, refresh_token = await auth.refresh_token(
        refresh_token=request.refresh_token
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/logout")
async def logout(
    request: LogoutRequest,
    current_user: CurrentUser,
    auth: AuthServiceDep,
):
    await auth.logout(
        user_id=current_user["user_id"],
        session_id=None if request.all_sessions else current_user.get("jti"),
        jti=current_user.get("jti"),
        tenant_id=current_user.get("tenant_id"),
    )
    return {"message": "Logged out successfully"}


@router.get("/oauth/{provider}")
async def oauth_login(provider: str):
    if provider not in ("google", "github"):
        raise HTTPException(status_code=400, detail="Unsupported OAuth provider")
    url = oauth_service.get_authorization_url(provider)
    return {"authorization_url": url}


@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str,
    state: str | None = None,
    auth: AuthServiceDep = None,
    req: Request = None,
):
    token_data = await oauth_service.exchange_code(provider, code)
    user_info = await oauth_service.get_user_info(provider, token_data.get("access_token", ""))
    try:
        user, access_token, refresh_token, _ = await auth.oauth_login(
            provider=user_info["provider"],
            provider_user_id=user_info["provider_user_id"],
            email=user_info["email"],
            full_name=user_info["full_name"],
            avatar_url=user_info.get("avatar_url"),
            access_token=user_info.get("access_token"),
            ip_address=req.client.host if req and req.client else None,
            user_agent=req.headers.get("user-agent") if req else None,
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )
    except MFARequiredError as e:
        return MFAChallengeResponse(challenge_token=e.challenge_token)


@router.post("/verify-email")
async def verify_email(request: VerifyEmailRequest, auth: AuthServiceDep):
    await auth.verify_email(request.token)
    return {"message": "Email verified successfully"}


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, auth: AuthServiceDep):
    await auth.forgot_password(request.email)
    return {"message": "Password reset email sent if account exists"}


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, auth: AuthServiceDep):
    await auth.reset_password(token=request.token, new_password=request.password)
    return {"message": "Password reset successful"}


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: CurrentUser,
    auth: AuthServiceDep,
    _mfa: Annotated[None, Depends(require_mfa)] = None,
):
    await auth.change_password(
        user_id=current_user["user_id"],
        current_password=request.current_password,
        new_password=request.new_password,
    )
    return {"message": "Password changed successfully"}


@router.get("/me")
async def get_me(
    current_user: CurrentUser,
    auth: AuthServiceDep,
):
    user = await auth.get_profile(current_user["user_id"])
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_email_verified=user.is_email_verified,
        is_active=user.is_active,
    )
