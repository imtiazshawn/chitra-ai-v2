from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


class Base(DeclarativeBase):
    pass


def _get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        database_url = settings.database_url.get_secret_value()
        if not database_url:
            raise RuntimeError("DATABASE_URL is not configured")
        # asyncpg driver — replace psycopg2 scheme
        async_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
        _engine = create_async_engine(async_url, pool_pre_ping=True)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=_get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_session_factory()() as session:
        yield session


async def ping_database() -> bool:
    database_url = settings.database_url.get_secret_value()
    if not database_url:
        return False
    try:
        async with _get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
