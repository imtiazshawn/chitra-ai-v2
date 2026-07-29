from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from app.workflow.schemas.script import Script


# ---------------------------------------------------------------------------
# Node names — single source of truth, avoids magic strings in graph.py
# ---------------------------------------------------------------------------
class Nodes:
    SCRIPT    = "generate_script"
    AUDIO     = "generate_audio"
    SYNC      = "sync_captions"
    ASSETS    = "fetch_assets"
    RENDER    = "render_video"


# ---------------------------------------------------------------------------
# Pipeline state — passed between every node in the graph
# Each field is Optional so nodes only fill what they produce
# ---------------------------------------------------------------------------
class PipelineState(BaseModel):

    # ── Input ────────────────────────────────────────────────────────────────
    job_id: str                         = Field(..., description="UUID of the Job row")
    topic:  str                         = Field(..., description="Video topic from user")

    # ── Node: generate_script ────────────────────────────────────────────────
    script: Script | None               = Field(None, description="Generated script segments")

    # ── Node: generate_audio ────────────────────────────────────────────────
    audio_path: str | None              = Field(None, description="Local/remote path to audio file")

    # ── Node: sync_captions ─────────────────────────────────────────────────
    manifest: dict[str, Any] | None     = Field(None, description="Word-level caption timing manifest")

    # ── Node: fetch_assets ──────────────────────────────────────────────────
    asset_links: list[str] | None       = Field(None, description="URLs/paths of fetched media assets")

    # ── Node: render_video ──────────────────────────────────────────────────
    output_video_path: str | None       = Field(None, description="Final rendered video path")

    # ── Error handling ───────────────────────────────────────────────────────
    error: str | None                   = Field(None, description="Error message if any node fails")
