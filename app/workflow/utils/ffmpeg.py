from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def _run(cmd: list[str]) -> None:
    """Run an FFmpeg command, raise on non-zero exit."""
    logger.debug("FFmpeg: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed:\n{result.stderr[-2000:]}")


# ---------------------------------------------------------------------------
# Step 1 — Trim + scale each clip to exact line duration at 1080x1920
# ---------------------------------------------------------------------------
def trim_and_scale(
    input_path: str,
    output_path: Path,
    duration: float,
) -> Path:
    _run([
        "ffmpeg", "-y",
        "-i", input_path,
        "-t", str(duration),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-an",                      # strip audio from clip — we use our own TTS audio
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-r", "30",
        str(output_path),
    ])
    return output_path


# ---------------------------------------------------------------------------
# Step 2 — Concatenate trimmed clips into one silent video
# ---------------------------------------------------------------------------
def concatenate(clip_paths: list[Path], output_path: Path) -> Path:
    concat_list = output_path.parent / f"{output_path.stem}_concat.txt"
    concat_list.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in clip_paths),
        encoding="utf-8",
    )
    _run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(output_path),
    ])
    concat_list.unlink(missing_ok=True)
    return output_path


# ---------------------------------------------------------------------------
# Step 3 — Mix TTS audio onto the concatenated video
# ---------------------------------------------------------------------------
def mix_audio(video_path: Path, audio_path: str, output_path: Path) -> Path:
    _run([
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", audio_path,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        str(output_path),
    ])
    return output_path


# ---------------------------------------------------------------------------
# Step 4 — Burn ASS subtitles into the final video
# ---------------------------------------------------------------------------
def burn_subtitles(video_path: Path, ass_path: Path, output_path: Path) -> Path:
    # On Windows, FFmpeg ass filter needs the path quoted and spaces escaped
    ass_str = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:").replace(" ", "\\ ")
    _run([
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", f"ass='{ass_str}'",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "copy",
        str(output_path),
    ])
    return output_path
