from collections.abc import AsyncGenerator

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import Client

from app.core.redis import get_redis
from app.core.supabase import get_supabase_admin, get_supabase_client
from app.db.session import get_db


async def redis_client() -> AsyncGenerator[Redis, None]:
    client = await get_redis()
    yield client


async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db():
        yield session


def supabase_admin() -> Client:
    return get_supabase_admin()


def supabase_client() -> Client:
    return get_supabase_client()
