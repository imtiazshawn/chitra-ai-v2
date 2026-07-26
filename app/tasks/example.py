import time

from app.core.celery_app import celery_app


@celery_app.task(name="app.tasks.example.ping", queue="default")
def ping_task(message: str = "pong") -> dict[str, str]:
    """Default queue — lightweight smoke-test task."""
    return {"message": message}


@celery_app.task(name="app.tasks.io.fetch_assets", queue="io_heavy", bind=True, max_retries=3)
def fetch_assets_task(self, job_id: str) -> dict[str, str]:
    """IO-heavy queue — simulates external API / DB calls."""
    try:
        time.sleep(0.5)  # simulate network latency
        return {"job_id": job_id, "status": "assets_fetched"}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)


@celery_app.task(name="app.tasks.cpu.render_video", queue="cpu_heavy", bind=True, max_retries=2)
def render_video_task(self, job_id: str) -> dict[str, str]:
    """CPU-heavy queue — simulates video rendering / ML inference."""
    try:
        time.sleep(1)  # simulate heavy computation
        return {"job_id": job_id, "status": "rendered"}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)
