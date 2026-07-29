from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
AUDIO_DIR = Path("outputs/audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# ElevenLabs — primary
# ---------------------------------------------------------------------------
ELEVENLABS_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"  # "George" — free tier voice


def _generate_elevenlabs(text: str, output_path: Path) -> None:
    from elevenlabs import ElevenLabs

    client = ElevenLabs(api_key=settings.elevenlabs_api_key.get_secret_value())
    audio = client.text_to_speech.convert(
        voice_id=ELEVENLABS_VOICE_ID,
        text=text,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )
    with open(output_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)


# ---------------------------------------------------------------------------
# edge-tts — fallback (free, no API key needed)
# ---------------------------------------------------------------------------
EDGE_TTS_VOICE = "en-US-ChristopherNeural"


async def _generate_edge_tts(text: str, output_path: Path) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, EDGE_TTS_VOICE)
    await communicate.save(str(output_path))


# ---------------------------------------------------------------------------
# Core — try ElevenLabs, fall back to edge-tts
# ---------------------------------------------------------------------------
def _generate_audio(text: str, job_id: str) -> Path:
    output_path = AUDIO_DIR / f"{job_id}.mp3"

    # Primary: ElevenLabs
    try:
        logger.info("[%s] generate_audio: trying ElevenLabs", job_id)
        _generate_elevenlabs(text, output_path)
        logger.info("[%s] generate_audio: ElevenLabs OK → %s", job_id, output_path)
        return output_path
    except Exception as exc:
        logger.warning("[%s] ElevenLabs failed (%s), falling back to edge-tts", job_id, exc)

    # Fallback: edge-tts
    try:
        logger.info("[%s] generate_audio: trying edge-tts", job_id)
        asyncio.run(_generate_edge_tts(text, output_path))
        logger.info("[%s] generate_audio: edge-tts OK → %s", job_id, output_path)
        return output_path
    except Exception as exc:
        raise RuntimeError(f"All TTS providers failed: {exc}") from exc


# ---------------------------------------------------------------------------
# LangGraph node
# ---------------------------------------------------------------------------
def generate_audio_node(state: Any) -> dict[str, Any]:
    if not state.script:
        return {"error": "audio_failed: no script in state"}

    logger.info("[%s] generate_audio: starting", state.job_id)
    try:
        path = _generate_audio(state.script.full_narration, state.job_id)
        return {"audio_path": str(path)}
    except Exception as exc:
        logger.error("[%s] generate_audio failed: %s", state.job_id, exc)
        return {"error": f"audio_failed: {exc}"}
