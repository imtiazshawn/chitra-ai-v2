from __future__ import annotations

from pydantic import BaseModel, Field


class Word(BaseModel):
    word: str
    start: float = Field(..., description="Start time in seconds")
    end: float   = Field(..., description="End time in seconds")


class Line(BaseModel):
    line_id: int
    text: str
    start: float
    end: float
    words: list[Word]
    asset_tags: list[str] = Field(default_factory=list, description="Visual search tags for this line")


class Manifest(BaseModel):
    job_id: str
    audio_path: str
    duration: float             = Field(..., description="Total audio duration in seconds")
    lines: list[Line]

    @property
    def total_words(self) -> int:
        return sum(len(line.words) for line in self.lines)
