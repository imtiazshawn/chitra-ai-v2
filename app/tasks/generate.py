from __future__ import annotations

import logging
import uuid

from sqlalchemy import update

from app.core.celery_app import celery_app
from app.db.session import SyncSession
from app.models.job import Job, JobStatus
from app.workflow.graph import pipeline
from app.workflow.state import PipelineState

logger = logging.getLogger(__name__)

# Node name → status written when that node starts
_NODE_STATUS: dict[str, JobStatus] = {
    "generate_script": JobStatus.SCRIPTING,
    "generate_audio":  JobStatus.AUDIO,
    "sync_captions":   JobStatus.SYNC,
    "fetch_assets":    JobStatus.ASSETS,
    "render_video":    JobStatus.RENDERING,
}


def _set_status(session, job_id: str, status: JobStatus, error: str | None = None) -> None:
    values: dict = {"status": status}
    if error:
        values["error_message"] = error
    session.execute(update(Job).where(Job.id == uuid.UUID(job_id)).values(**values))
    session.commit()


@celery_app.task(
    name="app.tasks.generate.run_pipeline",
    queue="cpu_heavy",
    bind=True,
    max_retries=0,
)
def run_pipeline(self, job_id: str, topic: str) -> dict:
    logger.info("[%s] pipeline started — topic: %s", job_id, topic)

    with SyncSession() as session:
        try:
            state = PipelineState(job_id=job_id, topic=topic)
            final_node_output: dict = {}

            for event in pipeline.stream(state):
                node_name = next(iter(event))
                node_output = event[node_name]

                # update DB status as each node completes
                status = _NODE_STATUS.get(node_name)
                if status:
                    _set_status(session, job_id, status)
                    logger.info("[%s] ✓ %s", job_id, node_name)

                final_node_output = node_output  # keep last

            # Check for pipeline error in final output
            error = final_node_output.get("error") if isinstance(final_node_output, dict) else None
            if error:
                _set_status(session, job_id, JobStatus.FAILED, error)
                logger.error("[%s] pipeline failed: %s", job_id, error)
                return {"job_id": job_id, "status": "FAILED", "error": error}

            output_path = final_node_output.get("output_video_path") if isinstance(final_node_output, dict) else None
            _set_status(session, job_id, JobStatus.COMPLETED)
            logger.info("[%s] pipeline completed → %s", job_id, output_path)
            return {"job_id": job_id, "status": "COMPLETED", "output": output_path}

        except Exception as exc:
            _set_status(session, job_id, JobStatus.FAILED, str(exc))
            logger.exception("[%s] unexpected error: %s", job_id, exc)
            raise
