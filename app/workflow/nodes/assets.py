from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.workflow.schemas.asset import AssetClip, AssetMap

logger = logging.getLogger(__name__)

ASSETS_DIR = Path("outputs/assets")
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

PEXELS_API_BASE  = "https://api.pexels.com/videos"
PREFERRED_WIDTH  = 1080
PREFERRED_HEIGHT = 1920
PER_PAGE         = 5       # fetch top 5 results, pick best resolution match


# ---------------------------------------------------------------------------
# Pexels client with tenacity retry
# ---------------------------------------------------------------------------
@retry(
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(4),
    reraise=True,
)
def _search_pexels(query: str) -> dict:
    headers = {"Authorization": settings.pexels_api_key.get_secret_value()}
    params  = {"query": query, "per_page": PER_PAGE, "orientation": "portrait"}

    with httpx.Client(timeout=15) as client:
        response = client.get(f"{PEXELS_API_BASE}/search", headers=headers, params=params)
        response.raise_for_status()
        return response.json()


# ---------------------------------------------------------------------------
# Pick best video file from Pexels result (closest to 1080p)
# ---------------------------------------------------------------------------
def _pick_best_file(video: dict) -> dict | None:
    files  = video.get("video_files", [])
    # prefer portrait files (height > width)
    portrait = [f for f in files if f.get("height", 0) > f.get("width", 0)]
    pool     = portrait if portrait else files
    hd       = [f for f in pool if f.get("height", 0) >= 1280]
    return min(hd, key=lambda f: abs(f["height"] - PREFERRED_HEIGHT)) if hd else (pool[0] if pool else None)


# ---------------------------------------------------------------------------
# Download video file
# ---------------------------------------------------------------------------
@retry(
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(3),
    reraise=True,
)
def _download_clip(url: str, dest: Path) -> None:
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        with client.stream("GET", url) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_bytes(chunk_size=8192):
                    f.write(chunk)


# ---------------------------------------------------------------------------
# Fetch + download one clip for a line
# ---------------------------------------------------------------------------
def _fetch_clip_for_line(line_id: int, tags: list[str], job_id: str, id_to_path: dict[int, str]) -> AssetClip | None:
    for query in tags:
        try:
            data   = _search_pexels(query)
            videos = data.get("videos", [])
            if not videos:
                continue

            video     = videos[0]
            best_file = _pick_best_file(video)
            if not best_file:
                continue

            video_id = video["id"]
            dest     = ASSETS_DIR / f"{job_id}_line{line_id}.mp4"

            # reuse already-downloaded file if same video_id seen before
            if video_id in id_to_path:
                logger.info("[%s] line %d: reusing cached clip (id=%d)", job_id, line_id, video_id)
            else:
                logger.info("[%s] downloading clip for line %d: %s", job_id, line_id, query)
                _download_clip(best_file["link"], dest)

            return AssetClip(
                line_id=line_id,
                query=query,
                pexels_video_id=video_id,
                local_path=id_to_path.get(video_id, str(dest)),
                duration=float(video.get("duration", 0)),
                width=best_file.get("width", 0),
                height=best_file.get("height", 0),
            )
        except Exception as exc:
            logger.warning("[%s] query %r failed: %s", job_id, query, exc)
            continue

    logger.warning("[%s] no clip found for line %d (tags: %s)", job_id, line_id, tags)
    return None


# ---------------------------------------------------------------------------
# LangGraph node
# ---------------------------------------------------------------------------
def fetch_assets_node(state: Any) -> dict[str, Any]:
    if not state.manifest:
        return {"error": "assets_failed: no manifest in state"}

    logger.info("[%s] fetch_assets: %d lines to process", state.job_id, len(state.manifest.lines))

    asset_map   = AssetMap(job_id=state.job_id)
    # cache: pexels_video_id -> local_path to avoid re-downloading the same clip
    id_to_path: dict[int, str] = {}

    for line in state.manifest.lines:
        if not line.asset_tags:
            logger.warning("[%s] line %d has no asset tags, skipping", state.job_id, line.line_id)
            continue

        clip = _fetch_clip_for_line(line.line_id, line.asset_tags, state.job_id, id_to_path)
        if clip:
            id_to_path[clip.pexels_video_id] = clip.local_path
            asset_map.clips.append(clip)

    if not asset_map.clips:
        return {"error": "assets_failed: no clips could be downloaded"}

    logger.info("[%s] fetch_assets: %d/%d clips downloaded", state.job_id, len(asset_map.clips), len(state.manifest.lines))
    return {"asset_links": asset_map}
