from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.models.user import User


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register(self, username: str, email: str, password: str) -> User:
        existing_user = await self.get_user_by_username(username)
        if existing_user:
            raise ValueError("Username already taken")

        existing_email = await self.get_user_by_email(email)
        if existing_email:
            raise ValueError("Email already registered")

        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            role="user",
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def authenticate(self, username: str, password: str) -> User:
        user = await self.get_user_by_username(username)
        if user is None:
            raise ValueError("Invalid username or password")
        if not verify_password(password, user.password_hash):
            raise ValueError("Invalid username or password")
        if not user.is_active:
            raise ValueError("Account is disabled")
        return user

    async def get_user_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    def create_tokens(self, user: User) -> dict:
        access_token = create_access_token(
            subject=user.id,
            extra_claims={"role": user.role, "username": user.username},
        )
        refresh_token = create_refresh_token(subject=user.id)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 1800,
        }

    async def refresh_access_token(self, refresh_token: str) -> dict:
        try:
            payload = decode_token(refresh_token)
        except ValueError:
            raise ValueError("Invalid refresh token")

        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")

        user_id = payload.get("sub")
        user = await self.get_user_by_id(int(user_id))
        if user is None:
            raise ValueError("User not found")

        return self.create_tokens(user)

    async def change_password(self, user_id: int, current_password: str, new_password: str) -> None:
        user = await self.get_user_by_id(user_id)
        if user is None:
            raise ValueError("User not found")
        if not verify_password(current_password, user.password_hash):
            raise ValueError("Current password is incorrect")
        user.password_hash = hash_password(new_password)
        await self.db.flush()
