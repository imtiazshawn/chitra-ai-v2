"""
Test: Audio Node (Module 2.3)
Run: python -m tests.test_audio_node
"""

from app.workflow.nodes.audio import generate_audio_node
from app.workflow.schemas.script import Scene, Script
from app.workflow.state import PipelineState

# Hardcoded script so we don't burn LLM credits on every audio test
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
    print("Narration text:")
    print(f"  {MOCK_SCRIPT.full_narration[:120]}...")
    print("-" * 60)

    state = PipelineState(job_id="test-audio-001", topic="Benefits of drinking water")
    state.script = MOCK_SCRIPT

    result = generate_audio_node(state)

    if result.get("error"):
        print("FAILED:", result["error"])
        return

    audio_path = result["audio_path"]
    print(f"Audio saved : {audio_path}")

    from pathlib import Path
    size_kb = Path(audio_path).stat().st_size / 1024
    print(f"File size   : {size_kb:.1f} KB")
    print("-" * 60)
    print("PASSED — open the file to listen to the audio")


if __name__ == "__main__":
    main()
