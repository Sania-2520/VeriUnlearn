from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _sync_database_url() -> str:
    url = settings.database_url
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    elif url.startswith("sqlite+aiosqlite://"):
        url = url.replace("sqlite+aiosqlite://", "sqlite://")
    return url


_is_sqlite = _sync_database_url().startswith("sqlite://")

_sync_engine = create_engine(
    _sync_database_url(),
    **({} if _is_sqlite else {"pool_size": 2, "max_overflow": 4}),
    pool_pre_ping=not _is_sqlite,
)

_SyncSessionLocal = sessionmaker(
    bind=_sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@contextmanager
def worker_session() -> Generator[Session, None, None]:
    session = _SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        logger.warning("Worker session failed, rolling back: %s", e)
        session.rollback()
        raise
    finally:
        session.close()
