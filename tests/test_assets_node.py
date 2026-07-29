"""
Test: Assets Node (Module 2.5)
Run: python -m tests.test_assets_node

Requires: outputs/audio/test-audio-001-manifest.json
Run test_sync_node.py first if the file doesn't exist.
"""

import json
from pathlib import Path

from app.workflow.nodes.assets import fetch_assets_node
from app.workflow.schemas.manifest import Manifest
from app.workflow.state import PipelineState

MANIFEST_PATH = "outputs/audio/test-audio-001-manifest.json"


def main():
    if not Path(MANIFEST_PATH).exists():
        print(f"Manifest not found: {MANIFEST_PATH}")
        print("Run: python -m tests.test_sync_node first")
        return

    manifest = Manifest.model_validate(json.loads(Path(MANIFEST_PATH).read_text()))

    print(f"Lines to fetch : {len(manifest.lines)}")
    print("-" * 60)

    state = PipelineState(job_id="test-audio-001", topic="Benefits of drinking water")
    state.manifest = manifest

    result = fetch_assets_node(state)

    if result.get("error"):
        print("FAILED:", result["error"])
        return

    asset_map = result["asset_links"]
    print(f"Clips downloaded : {len(asset_map.clips)}/{len(manifest.lines)}")
    print()

    for clip in asset_map.clips:
        size_mb = Path(clip.local_path).stat().st_size / (1024 * 1024)
        print(f"Line {clip.line_id}")
        print(f"  Query      : {clip.query}")
        print(f"  Pexels ID  : {clip.pexels_video_id}")
        print(f"  Resolution : {clip.width}x{clip.height}")
        print(f"  Duration   : {clip.duration}s")
        print(f"  File       : {clip.local_path}  ({size_mb:.1f} MB)")
        print()

    print("-" * 60)
    print("PASSED")


if __name__ == "__main__":
    main()
