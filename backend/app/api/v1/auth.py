from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import DatabaseDep, CurrentUser
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    UserResponse,
    PasswordChangeRequest,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: DatabaseDep):
    service = AuthService(db)
    try:
        user = await service.register(
            username=body.username,
            email=body.email,
            password=body.password,
        )
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DatabaseDep):
    service = AuthService(db)
    try:
        user = await service.authenticate(username=body.username, password=body.password)
        return service.create_tokens(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: DatabaseDep):
    service = AuthService(db)
    try:
        return await service.refresh_access_token(body.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_me(user: CurrentUser):
    return user


@router.post("/change-password")
async def change_password(body: PasswordChangeRequest, user: CurrentUser, db: DatabaseDep):
    service = AuthService(db)
    try:
        await service.change_password(
            user_id=user.id,
            current_password=body.current_password,
            new_password=body.new_password,
        )
        return {"message": "Password changed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
