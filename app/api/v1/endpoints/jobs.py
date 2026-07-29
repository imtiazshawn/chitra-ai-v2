from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.models.job import Job, JobStatus
from app.tasks.generate import run_pipeline

router = APIRouter()

# ---------------------------------------------------------------------------
# Progress map — what % complete each status represents
# ---------------------------------------------------------------------------
_PROGRESS: dict[JobStatus, int] = {
    JobStatus.QUEUED:     0,
    JobStatus.SCRIPTING:  10,
    JobStatus.AUDIO:      30,
    JobStatus.SYNC:       50,
    JobStatus.ASSETS:     70,
    JobStatus.RENDERING:  85,
    JobStatus.COMPLETED:  100,
    JobStatus.FAILED:     0,
}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class GenerateRequest(BaseModel):
    topic: str


class GenerateResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    topic: str
    status: str
    progress: int
    video_url: str | None
    error_message: str | None


# ---------------------------------------------------------------------------
# POST /generate
# ---------------------------------------------------------------------------
@router.post("/generate", response_model=GenerateResponse, status_code=202)
async def generate_video(
    body: GenerateRequest,
    db: AsyncSession = Depends(db_session),
) -> GenerateResponse:
    job = Job(
        id=uuid.uuid4(),
        topic=body.topic,
        status=JobStatus.QUEUED,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    run_pipeline.delay(str(job.id), job.topic)

    return GenerateResponse(job_id=str(job.id), status=job.status)


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}
# ---------------------------------------------------------------------------
@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(db_session),
) -> JobStatusResponse:
    try:
        uid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job_id format")

    result = await db.execute(select(Job).where(Job.id == uid))
    job: Job | None = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    video_url = None
    if job.status == JobStatus.COMPLETED:
        video_path = Path(f"outputs/video/{job.id}.mp4")
        if video_path.exists():
            video_url = f"/outputs/video/{job.id}.mp4"

    return JobStatusResponse(
        job_id=str(job.id),
        topic=job.topic,
        status=job.status,
        progress=_PROGRESS.get(job.status, 0),
        video_url=video_url,
        error_message=job.error_message,
    )
