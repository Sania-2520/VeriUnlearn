from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import INET, UUID

@compiles(INET, "sqlite")
def compile_inet_sqlite(element, compiler, **kw):
    return "VARCHAR(45)"

@compiles(UUID, "sqlite")
def compile_uuid_sqlite(element, compiler, **kw):
    return "VARCHAR(36)"

class Base(DeclarativeBase):
    pass


class DatabaseManager:
    _engine: AsyncEngine | None = None
    _session_factory: async_sessionmaker[AsyncSession] | None = None

    def __init__(self) -> None:
        self._engine = None
        self._session_factory = None

    async def initialize(self) -> None:
        is_sqlite = settings.database_url.startswith("sqlite")
        kwargs = {
            "echo": settings.database_echo,
            "pool_pre_ping": True,
        }
        if not is_sqlite:
            kwargs.update({
                "pool_size": settings.database_pool_size,
                "max_overflow": settings.database_max_overflow,
                "pool_recycle": 3600,
            })
        self._engine = create_async_engine(
            settings.database_url,
            **kwargs
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

    async def close(self) -> None:
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    @property
    def engine(self) -> AsyncEngine:
        if not self._engine:
            raise RuntimeError("Database engine not initialized. Call initialize() first.")
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if not self._session_factory:
            raise RuntimeError(
                "Session factory not initialized. Call initialize() first."
            )
        return self._session_factory

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                logger.warning("Session commit failed, rolling back: %s", e)
                await session.rollback()
                raise
            finally:
                await session.close()

    async def get_transaction_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.session_factory() as session:
            try:
                await session.begin()
                yield session
                await session.commit()
            except Exception as e:
                logger.warning("Transaction failed, rolling back: %s", e)
                await session.rollback()
                raise
            finally:
                await session.close()


db = DatabaseManager()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in db.get_session():
        yield session
