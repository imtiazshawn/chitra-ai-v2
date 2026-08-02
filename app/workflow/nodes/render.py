from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.services.video_storage import upload_rendered_video
from app.workflow.utils.ffmpeg import burn_subtitles, concatenate, mix_audio, trim_and_scale
from app.workflow.utils.subtitle import build_ass

logger = logging.getLogger(__name__)

VIDEO_DIR = Path("outputs/video")
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

TEMP_DIR = Path("outputs/video/tmp")
TEMP_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# LangGraph node
# ---------------------------------------------------------------------------
def render_video_node(state: Any) -> dict[str, Any]:
    if not state.manifest:
        return {"error": "render_failed: no manifest in state"}
    if not state.audio_path:
        return {"error": "render_failed: no audio_path in state"}
    if not state.asset_links or not state.asset_links.clips:
        return {"error": "render_failed: no asset clips in state"}

    job_id   = state.job_id
    manifest = state.manifest
    clips    = state.asset_links

    logger.info("[%s] render_video: starting", job_id)

    try:
        # ── Step 1: trim + scale each clip to its slot duration ─────────────
        # Slot = line.start → next_line.start (includes trailing silence gap).
        # Last line slot = line.start → audio end.
        trimmed: list[Path] = []
        lines = manifest.lines
        audio_duration = manifest.duration
        for i, line in enumerate(lines):
            clip = clips.get_clip(line.line_id)
            if not clip:
                logger.warning("[%s] no clip for line %d, skipping", job_id, line.line_id)
                continue

            slot_end = lines[i + 1].start if i + 1 < len(lines) else audio_duration
            slot_duration = round(slot_end - line.start, 3)
            out = TEMP_DIR / f"{job_id}_trimmed_line{line.line_id}.mp4"
            trim_and_scale(clip.local_path, out, slot_duration)
            trimmed.append(out)
            logger.info("[%s] trimmed line %d (%.2fs)", job_id, line.line_id, slot_duration)

        if not trimmed:
            return {"error": "render_failed: no trimmed clips produced"}

        # ── Step 2: concatenate trimmed clips ────────────────────────────────
        concat_path = TEMP_DIR / f"{job_id}_concat.mp4"
        concatenate(trimmed, concat_path)
        logger.info("[%s] concatenated %d clips", job_id, len(trimmed))

        # ── Step 3: mix TTS audio ────────────────────────────────────────────
        mixed_path = TEMP_DIR / f"{job_id}_mixed.mp4"
        mix_audio(concat_path, state.audio_path, mixed_path)
        logger.info("[%s] audio mixed", job_id)

        # ── Step 4: generate ASS subtitles ───────────────────────────────────
        ass_path = TEMP_DIR / f"{job_id}.ass"
        build_ass(manifest, ass_path)
        logger.info("[%s] ASS subtitles generated", job_id)

        # ── Step 5: burn subtitles into final video ──────────────────────────
        final_path = VIDEO_DIR / f"{job_id}.mp4"
        burn_subtitles(mixed_path, ass_path, final_path)
        logger.info("[%s] render complete: %s", job_id, final_path)

        # cleanup temp files
        for f in [concat_path, mixed_path, ass_path] + trimmed:
            f.unlink(missing_ok=True)

        video_url = upload_rendered_video(final_path, job_id)
        logger.info("[%s] uploaded to Supabase Storage: %s", job_id, video_url)

        return {"video_url": video_url}

    except Exception as exc:
        logger.error("[%s] render_video failed: %s", job_id, exc)
        return {"error": f"render_failed: {exc}"}
