from __future__ import annotations

from pathlib import Path

from app.workflow.schemas.manifest import Manifest


# ---------------------------------------------------------------------------
# ASS header — 9:16 canvas (1080x1920), bold white text, yellow highlight
# ---------------------------------------------------------------------------
_ASS_HEADER = """\
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,72,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,60,60,120,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _ts(seconds: float) -> str:
    """Convert seconds to ASS timestamp H:MM:SS.cc"""
    h  = int(seconds // 3600)
    m  = int((seconds % 3600) // 60)
    s  = int(seconds % 60)
    cs = int(round((seconds % 1) * 100))
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def build_ass(manifest: Manifest, output_path: Path) -> Path:
    """
    Build an ASS subtitle file where each word is highlighted yellow
    as it is spoken (karaoke style).
    """
    lines_ass: list[str] = []

    for line in manifest.lines:
        if not line.words:
            continue

        # Build karaoke tags: {\\kf<duration_cs>}word
        karaoke_parts: list[str] = []
        for word in line.words:
            duration_cs = max(1, int(round((word.end - word.start) * 100)))
            karaoke_parts.append(f"{{\\kf{duration_cs}}}{word.word}")

        text = " ".join(karaoke_parts)
        lines_ass.append(
            f"Dialogue: 0,{_ts(line.start)},{_ts(line.end)},Default,,0,0,0,,{text}"
        )

    output_path.write_text(_ASS_HEADER + "\n".join(lines_ass), encoding="utf-8")
    return output_path
