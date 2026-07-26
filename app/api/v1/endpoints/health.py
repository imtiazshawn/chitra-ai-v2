from fastapi import APIRouter

from app.core.redis import ping_redis
from app.core.supabase import ping_supabase
from app.db.session import ping_database

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str | bool]:
    redis_ok = await ping_redis()
    supabase_ok = await ping_supabase()
    database_ok = await ping_database()

    checks = {"redis": redis_ok, "supabase": supabase_ok, "database": database_ok}
    all_ok = all(checks.values())
    any_ok = any(checks.values())

    if all_ok:
        status = "ok"
    elif any_ok or supabase_ok:
        status = "degraded"
    else:
        status = "down"

    return {"status": status, **checks}
