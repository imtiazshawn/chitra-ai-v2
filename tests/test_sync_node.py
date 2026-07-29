"""
Test: Sync Node (Module 2.4)
Run: python -m tests.test_sync_node

Requires: outputs/audio/test-audio-001.mp3
Run test_audio_node.py first if the file doesn't exist.
"""

from pathlib import Path

from app.workflow.nodes.sync import sync_captions_node
from app.workflow.schemas.script import Scene, Script
from app.workflow.state import PipelineState

AUDIO_PATH = "outputs/audio/test-audio-001.mp3"

MOCK_SCRIPT = Script(
    hook="Did you know water covers 71% of the Earth?",
    scenes=[
        Scene(
            scene_number=1,
            narrator_text="Staying hydrated improves focus, energy, and overall health.",
            visual_keywords=["water glass", "hydration", "healthy lifestyle"],
            duration_seconds=8.0,
        ),
        Scene(
            scene_number=2,
            narrator_text="Even mild dehydration can cause fatigue and headaches.",
            visual_keywords=["tired person", "headache", "dehydration"],
            duration_seconds=7.0,
        ),
    ],
    call_to_action="Drink 8 glasses of water today and feel the difference!",
)


def main():
    if not Path(AUDIO_PATH).exists():
        print(f"Audio file not found: {AUDIO_PATH}")
        print("Run: python -m tests.test_audio_node first")
        return

    print(f"Audio file : {AUDIO_PATH}")
    print("-" * 60)

    state = PipelineState(job_id="test-audio-001", topic="Benefits of drinking water")
    state.audio_path = AUDIO_PATH
    state.script = MOCK_SCRIPT

    result = sync_captions_node(state)

    if result.get("error"):
        print("FAILED:", result["error"])
        return

    manifest = result["manifest"]
    print(f"Duration   : {manifest.duration}s")
    print(f"Lines      : {len(manifest.lines)}")
    print(f"Total words: {manifest.total_words}")
    print()

    for line in manifest.lines:
        print(f"Line {line.line_id}  [{line.start}s -> {line.end}s]")
        print(f"  Text       : {line.text}")
        print(f"  Asset tags : {line.asset_tags}")
        print(f"  Words      : {[(w.word, w.start) for w in line.words[:4]]}...")
        print()

    # Save manifest as JSON so you can inspect it
    import json
    out = Path("outputs/audio/test-audio-001-manifest.json")
    out.write_text(json.dumps(manifest.model_dump(), indent=2))
    print(f"Manifest saved : {out}")
    print("-" * 60)
    print("PASSED")


if __name__ == "__main__":
    main()
