from __future__ import annotations

from pydantic import BaseModel, Field


class AssetClip(BaseModel):
    line_id: int
    query: str                          = Field(..., description="Search query used to find this clip")
    pexels_video_id: int
    local_path: str                     = Field(..., description="Downloaded file path on disk")
    duration: float                     = Field(..., description="Clip duration in seconds")
    width: int
    height: int


class AssetMap(BaseModel):
    job_id: str
    clips: list[AssetClip]              = Field(default_factory=list)

    def get_clip(self, line_id: int) -> AssetClip | None:
        return next((c for c in self.clips if c.line_id == line_id), None)
