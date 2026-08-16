from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession
from app.api.serializers import user_out
from app.core.exceptions import UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.user_repo import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.schemas.common import MessageResponse
from app.services.audit import AuditService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(payload: RegisterRequest, db: DbSession) -> TokenResponse:
    repo = UserRepository(db)
    user = await repo.create(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role="operator",
    )
    await AuditService(db).log(
        event_type="auth.register", actor=user.id, subject=user.email, payload={"role": user.role}
    )
    token = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token, user=UserOut(**user_out(user)))


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    repo = UserRepository(db)
    user = await repo.get_by_email(payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedError("Invalid credentials")
    if not user.is_active:
        raise UnauthorizedError("Account disabled")
    await AuditService(db).log(event_type="auth.login", actor=user.id, subject=user.email)
    token = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token, user=UserOut(**user_out(user)))


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser, db: DbSession) -> UserOut:
    repo = UserRepository(db)
    return UserOut(**user_out(await repo.get(user["sub"])))


@router.post("/logout", response_model=MessageResponse)
async def logout(user: CurrentUser, db: DbSession) -> MessageResponse:
    await AuditService(db).log(event_type="auth.logout", actor=user["sub"])
    return MessageResponse(message="Logged out")
