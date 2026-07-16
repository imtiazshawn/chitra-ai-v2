from fastapi import APIRouter

from app.core.redis import ping_redis

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str | bool]:
    redis_ok = await ping_redis()
    return {
        "status": "ok" if redis_ok else "degraded",
        "redis": redis_ok,
    }
