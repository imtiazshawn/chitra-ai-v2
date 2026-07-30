from collections.abc import AsyncGenerator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


def _clean_url(url: str) -> str:
    """Strip pgbouncer=true and other non-SQLAlchemy query params."""
    parsed = urlparse(url)
    params = {k: v for k, v in parse_qs(parsed.query).items() if k != "pgbouncer"}
    cleaned = parsed._replace(query=urlencode(params, doseq=True))
    return urlunparse(cleaned)


# ---------------------------------------------------------------------------
# Sync engine — used by Celery workers (no async runtime)
# ---------------------------------------------------------------------------
_sync_engine = None


def _get_sync_engine():
    global _sync_engine
    if _sync_engine is None:
        # Use DIRECT_URL (port 5432) for sync/Celery — pgbouncer pooler is incompatible with psycopg2
        raw = settings.direct_url.get_secret_value() or settings.database_url.get_secret_value()
        url = _clean_url(raw)
        sync_url = url.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql://", "postgresql+psycopg2://")
        _sync_engine = create_engine(sync_url, pool_pre_ping=True)
    return _sync_engine


SyncSession: sessionmaker[Session] = sessionmaker(
    bind=None, autocommit=False, autoflush=False, expire_on_commit=False
)


def _init_sync_session() -> None:
    SyncSession.configure(bind=_get_sync_engine())


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


class Base(DeclarativeBase):
    pass


_init_sync_session()  # bind sync engine after Base is defined


def _get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        database_url = _clean_url(settings.database_url.get_secret_value())
        if not database_url:
            raise RuntimeError("DATABASE_URL is not configured")
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
    try:
        async with _get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
