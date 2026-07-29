from __future__ import annotations

from pydantic import BaseModel, Field


class Scene(BaseModel):
    scene_number: int           = Field(..., ge=1, description="Scene index starting at 1")
    narrator_text: str          = Field(..., min_length=10, description="Spoken narration for this scene")
    visual_keywords: list[str]  = Field(..., min_length=1, description="Search keywords for stock footage")
    duration_seconds: float     = Field(..., gt=0, le=30, description="Estimated scene duration")


class Script(BaseModel):
    hook: str           = Field(..., min_length=10, description="Opening hook sentence to grab attention")
    scenes: list[Scene] = Field(..., min_length=1, max_length=10, description="Ordered list of scenes")
    call_to_action: str = Field(..., min_length=5, description="Closing call-to-action line")

    @property
    def full_narration(self) -> str:
        """Concatenated narration text across all scenes — used by TTS node."""
        parts = [self.hook] + [s.narrator_text for s in self.scenes] + [self.call_to_action]
        return " ".join(parts)

    @property
    def all_visual_keywords(self) -> list[str]:
        """Flat list of all visual keywords across scenes — used by assets node."""
        return [kw for scene in self.scenes for kw in scene.visual_keywords]
