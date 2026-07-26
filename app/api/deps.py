from collections.abc import AsyncGenerator, Generator

from redis.asyncio import Redis
from sqlalchemy.orm import Session
from supabase import Client

from app.core.redis import get_redis
from app.core.supabase import get_supabase_admin, get_supabase_client
from app.db.session import get_db


async def redis_client() -> AsyncGenerator[Redis, None]:
    client = await get_redis()
    yield client


def db_session() -> Generator[Session, None, None]:
    yield from get_db()


def supabase_admin() -> Client:
    return get_supabase_admin()


def supabase_client() -> Client:
    return get_supabase_client()
