"""
Test: Scripting Node (Module 2.2)
Run: python tests/test_script_node.py
"""

from app.workflow.graph import pipeline
from app.workflow.state import PipelineState

TOPIC = "The future of solar energy"


def main():
    print(f"Topic: {TOPIC}")
    print("-" * 60)

    result = pipeline.invoke(PipelineState(job_id="test-script-001", topic=TOPIC))
    script = result.get("script")

    if not script:
        print("FAILED:", result.get("error"))
        return

    print(f"HOOK: {script.hook}\n")

    for scene in script.scenes:
        print(f"Scene {scene.scene_number}  ({scene.duration_seconds}s)")
        print(f"  Narration : {scene.narrator_text}")
        print(f"  Keywords  : {scene.visual_keywords}")
        print()

    print(f"CTA: {script.call_to_action}")
    print("-" * 60)
    print(f"Total scenes   : {len(script.scenes)}")
    print(f"Full narration : {script.full_narration[:120]}...")
    print(f"All keywords   : {script.all_visual_keywords}")


if __name__ == "__main__":
    main()
