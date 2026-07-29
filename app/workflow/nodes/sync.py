from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.workflow.schemas.manifest import Line, Manifest, Word

logger = logging.getLogger(__name__)

# faster-whisper model — "base" balances speed vs accuracy, runs on CPU
WHISPER_MODEL  = "base"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE = "int8"   # lightest compute type for CPU


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------
def _transcribe(audio_path: str) -> tuple[list, float]:
    """Returns (segments, duration). Loads model lazily on first call."""
    from faster_whisper import WhisperModel

    model = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE)
    segments, info = model.transcribe(
        audio_path,
        word_timestamps=True,
        language="en",
    )
    return list(segments), info.duration


# ---------------------------------------------------------------------------
# Manifest builder
# ---------------------------------------------------------------------------
def _build_manifest(
    segments: list,
    duration: float,
    audio_path: str,
    job_id: str,
    asset_tags_per_scene: list[list[str]],
) -> Manifest:
    lines: list[Line] = []
    line_id = 0

    for seg_idx, segment in enumerate(segments):
        words: list[Word] = []

        for w in (segment.words or []):
            words.append(Word(
                word=w.word.strip(),
                start=round(w.start, 3),
                end=round(w.end, 3),
            ))

        if not words:
            continue

        # Map segment index → scene asset tags (cycle if more segments than scenes)
        tags = asset_tags_per_scene[seg_idx % len(asset_tags_per_scene)] \
            if asset_tags_per_scene else []

        lines.append(Line(
            line_id=line_id,
            text=segment.text.strip(),
            start=round(segment.start, 3),
            end=round(segment.end, 3),
            words=words,
            asset_tags=tags,
        ))
        line_id += 1

    return Manifest(
        job_id=job_id,
        audio_path=audio_path,
        duration=round(duration, 3),
        lines=lines,
    )


# ---------------------------------------------------------------------------
# LangGraph node
# ---------------------------------------------------------------------------
def sync_captions_node(state: Any) -> dict[str, Any]:
    if not state.audio_path:
        return {"error": "sync_failed: no audio_path in state"}
    if not Path(state.audio_path).exists():
        return {"error": f"sync_failed: audio file not found at {state.audio_path}"}

    logger.info("[%s] sync_captions: transcribing %s", state.job_id, state.audio_path)
    try:
        segments, duration = _transcribe(state.audio_path)

        # Pull asset tags from script scenes if available
        asset_tags_per_scene: list[list[str]] = []
        if state.script:
            asset_tags_per_scene = [s.visual_keywords for s in state.script.scenes]

        manifest = _build_manifest(
            segments=segments,
            duration=duration,
            audio_path=state.audio_path,
            job_id=state.job_id,
            asset_tags_per_scene=asset_tags_per_scene,
        )

        logger.info(
            "[%s] sync_captions: %d lines, %d words, %.1fs",
            state.job_id, len(manifest.lines), manifest.total_words, manifest.duration,
        )
        return {"manifest": manifest}

    except Exception as exc:
        logger.error("[%s] sync_captions failed: %s", state.job_id, exc)
        return {"error": f"sync_failed: {exc}"}
