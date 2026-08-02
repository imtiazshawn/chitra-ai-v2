"""
Test: Render Node (Module 2.6)
Run: python -m tests.test_render_node

Requires:
  - outputs/audio/test-audio-001.mp3        (from test_audio_node)
  - outputs/audio/test-audio-001-manifest.json  (from test_sync_node)
  - outputs/assets/test-audio-001_line*.mp4  (from test_assets_node)
"""

import json
from pathlib import Path

from app.workflow.nodes.render import render_video_node
from app.workflow.schemas.asset import AssetClip, AssetMap
from app.workflow.schemas.manifest import Manifest
from app.workflow.state import PipelineState

AUDIO_PATH    = "outputs/audio/test-audio-001.mp3"
MANIFEST_PATH = "outputs/audio/test-audio-001-manifest.json"
ASSETS_DIR    = Path("outputs/assets")
JOB_ID        = "test-audio-001"


def main():
    # Validate prerequisites
    for p in [AUDIO_PATH, MANIFEST_PATH]:
        if not Path(p).exists():
            print(f"Missing: {p}")
            print("Run previous node tests first.")
            return

    manifest = Manifest.model_validate(json.loads(Path(MANIFEST_PATH).read_text()))

    # Rebuild AssetMap from downloaded files.
    # Lines that were deduplicated share the path of the first line that downloaded that clip.
    asset_map = AssetMap(job_id=JOB_ID)
    existing = sorted(ASSETS_DIR.glob(f"{JOB_ID}_line*.mp4"))  # sorted by line number
    if not existing:
        print("No asset clips found. Run: python -m tests.test_assets_node first")
        return

    # Build line_id -> path from files actually on disk
    disk_map: dict[int, Path] = {}
    for p in existing:
        try:
            lid = int(p.stem.split("_line")[1])
            disk_map[lid] = p
        except (IndexError, ValueError):
            pass

    # For lines with no file on disk, reuse the nearest available clip
    available = sorted(disk_map.keys())
    for line in manifest.lines:
        if line.line_id in disk_map:
            clip_path = disk_map[line.line_id]
        else:
            # pick the closest line_id that has a file
            closest = min(available, key=lambda x: abs(x - line.line_id))
            clip_path = disk_map[closest]
        asset_map.clips.append(AssetClip(
            line_id=line.line_id,
            query=line.asset_tags[0] if line.asset_tags else "unknown",
            pexels_video_id=0,
            local_path=str(clip_path),
            duration=line.end - line.start,
            width=1080,
            height=1920,
        ))

    print(f"Lines    : {len(manifest.lines)}")
    print(f"Clips    : {len(asset_map.clips)}")
    print(f"Audio    : {AUDIO_PATH}")
    print("-" * 60)

    state = PipelineState(job_id=JOB_ID, topic="Benefits of drinking water")
    state.audio_path = AUDIO_PATH
    state.manifest   = manifest
    state.asset_links = asset_map

    result = render_video_node(state)

    if result.get("error"):
        print("FAILED:", result["error"])
        return

    video_url = result.get("video_url")
    print(f"Video URL: {video_url}")
    print("-" * 60)
    print("PASSED — open the URL to watch the video")


if __name__ == "__main__":
    main()
