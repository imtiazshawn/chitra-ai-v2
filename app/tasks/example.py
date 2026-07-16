import time

from app.core.celery_app import celery_app


@celery_app.task(name="app.tasks.example.ping")
def ping_task(message: str = "pong") -> dict[str, str]:
    time.sleep(1)
    return {"message": message}
