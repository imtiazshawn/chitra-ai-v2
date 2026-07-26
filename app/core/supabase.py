from functools import lru_cache

import httpx
from supabase import Client, create_client

from app.core.config import settings


@lru_cache
def get_supabase_admin() -> Client:
    """Server-side client (service role). Bypasses RLS — use only in trusted backend code."""
    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key.get_secret_value(),
    )


@lru_cache
def get_supabase_client() -> Client:
    """Public anon client. Respects Row Level Security policies."""
    return create_client(
        settings.supabase_url,
        settings.supabase_anon_key.get_secret_value(),
    )


async def ping_supabase() -> bool:
    if not settings.supabase_url:
        return False

    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/health"
    headers = {"apikey": settings.supabase_anon_key.get_secret_value()}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, headers=headers)
            return response.status_code == 200
    except httpx.HTTPError:
        return False
