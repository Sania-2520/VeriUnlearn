from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.db.models import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, *, email: str, full_name: str, password_hash: str, role: str = "operator") -> User:
        existing = await self.get_by_email(email)
        if existing is not None:
            raise ConflictError(f"User with email {email} already exists")
        user = User(email=email, full_name=full_name, password_hash=password_hash, role=role)
        return await self.add(user)
