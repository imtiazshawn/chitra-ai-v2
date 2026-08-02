from __future__ import annotations

import logging
import traceback
import uuid
from datetime import datetime, timezone

from sqlalchemy import update

from app.core.celery_app import celery_app
from app.db.session import SyncSession
from app.models.job import Job, JobStatus
from app.workflow.graph import pipeline
from app.workflow.state import PipelineState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Node → (status, step label, progress %)
# Written to DB as each node COMPLETES
# ---------------------------------------------------------------------------
_NODE_META: dict[str, tuple[JobStatus, str, int]] = {
    "generate_script": (JobStatus.SCRIPTING, "Script generated",   10),
    "generate_audio":  (JobStatus.AUDIO,     "Audio generated",    30),
    "sync_captions":   (JobStatus.SYNC,      "Captions synced",    50),
    "fetch_assets":    (JobStatus.ASSETS,    "Assets downloaded",  70),
    "render_video":    (JobStatus.RENDERING, "Video rendering",    85),
}


# ---------------------------------------------------------------------------
# DB helpers (sync — runs inside Celery worker)
# ---------------------------------------------------------------------------
def _update_job(
    session,
    job_id: str,
    status: JobStatus,
    step_data: dict | None = None,
    error: str | None = None,
    video_url: str | None = None,
) -> None:
    values: dict = {
        "status": status,
        "updated_at": datetime.now(timezone.utc),
    }
    if step_data is not None:
        values["current_step_data"] = step_data
    if error is not None:
        values["error_message"] = error
    if video_url is not None:
        values["video_url"] = video_url

    session.execute(update(Job).where(Job.id == uuid.UUID(job_id)).values(**values))
    session.commit()


def _fail_job(job_id: str, error: str) -> None:
    """Standalone failure writer — used by on_failure where no session exists."""
    try:
        with SyncSession() as session:
            _update_job(
                session,
                job_id,
                JobStatus.FAILED,
                step_data={"failed_at": datetime.now(timezone.utc).isoformat()},
                error=error,
            )
    except Exception as db_exc:
        logger.error("[%s] could not write FAILED status to DB: %s", job_id, db_exc)


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------
class PipelineTask(celery_app.Task):
    """Base class that provides on_failure hook."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        job_id = kwargs.get("job_id") or (args[0] if args else None)
        if job_id:
            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            logger.error("[%s] on_failure: %s", job_id, tb)
            _fail_job(job_id, tb)
        super().on_failure(exc, task_id, args, kwargs, einfo)


@celery_app.task(
    name="app.tasks.generate.run_pipeline",
    base=PipelineTask,
    queue="cpu_heavy",
    bind=True,
    max_retries=0,
)
def run_pipeline(self, job_id: str, topic: str) -> dict:
    logger.info("[%s] pipeline started — topic: %s", job_id, topic)

    with SyncSession() as session:
        state = PipelineState(job_id=job_id, topic=topic)

        for event in pipeline.stream(state):
            node_name = next(iter(event))
            node_output = event[node_name]

            meta = _NODE_META.get(node_name)
            if not meta:
                continue

            status, label, progress = meta

            # Build current_step_data snapshot
            step_data = {
                "node":       node_name,
                "label":      label,
                "progress":   progress,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }

            # Capture node-specific summary fields
            if node_name == "generate_script" and isinstance(node_output, dict):
                script = node_output.get("script")
                if script:
                    step_data["scenes"] = len(getattr(script, "scenes", []))

            elif node_name == "generate_audio" and isinstance(node_output, dict):
                step_data["audio_path"] = node_output.get("audio_path")

            elif node_name == "sync_captions" and isinstance(node_output, dict):
                manifest = node_output.get("manifest")
                if manifest:
                    step_data["lines"]       = len(getattr(manifest, "lines", []))
                    step_data["total_words"] = getattr(manifest, "total_words", None)
                    step_data["duration"]    = getattr(manifest, "duration", None)

            elif node_name == "fetch_assets" and isinstance(node_output, dict):
                asset_links = node_output.get("asset_links")
                if asset_links:
                    step_data["clips_downloaded"] = len(getattr(asset_links, "clips", []))

            elif node_name == "render_video" and isinstance(node_output, dict):
                step_data["video_url"] = node_output.get("video_url")

            # Check for pipeline-level error returned by a node
            if isinstance(node_output, dict) and node_output.get("error"):
                error_msg = node_output["error"]
                step_data["error"] = error_msg
                _update_job(session, job_id, JobStatus.FAILED, step_data, error_msg)
                logger.error("[%s] node %s returned error: %s", job_id, node_name, error_msg)
                return {"job_id": job_id, "status": "FAILED", "error": error_msg}

            render_video_url = (
                node_output.get("video_url")
                if node_name == "render_video" and isinstance(node_output, dict)
                else None
            )
            _update_job(session, job_id, status, step_data, video_url=render_video_url)
            logger.info("[%s] ✓ %-20s  progress=%d%%", job_id, node_name, progress)

        # All nodes completed — mark COMPLETED
        final_step = {
            "node":         "completed",
            "label":        "Pipeline complete",
            "progress":     100,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        _update_job(session, job_id, JobStatus.COMPLETED, final_step)
        logger.info("[%s] pipeline COMPLETED", job_id)
        return {"job_id": job_id, "status": "COMPLETED"}
