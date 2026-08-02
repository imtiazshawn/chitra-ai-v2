from __future__ import annotations

import os
from pathlib import Path

from app.core.config import settings
from app.core.supabase import get_supabase_admin


def upload_rendered_video(local_path: str | Path, job_id: str) -> str:
    """Upload a rendered MP4 to Supabase Storage and return its public URL."""
    if not settings.supabase_url:
        raise RuntimeError("SUPABASE_URL is not configured")

    path = Path(local_path)
    if not path.is_file():
        raise FileNotFoundError(f"Rendered video not found: {path}")

    storage_path = f"{job_id}.mp4"
    bucket = settings.supabase_video_bucket
    supabase = get_supabase_admin()

    with path.open("rb") as video_file:
        supabase.storage.from_(bucket).upload(
            storage_path,
            video_file.read(),
            file_options={"content-type": "video/mp4", "upsert": "true"},
        )

    public_url = supabase.storage.from_(bucket).get_public_url(storage_path)
    os.remove(path)

    return public_url
