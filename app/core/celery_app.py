from celery import Celery
from kombu import Exchange, Queue

from app.core.config import settings

# ---------------------------------------------------------------------------
# Exchanges
# ---------------------------------------------------------------------------
default_exchange = Exchange("default", type="direct")
io_exchange = Exchange("io_heavy", type="direct")
cpu_exchange = Exchange("cpu_heavy", type="direct")

# ---------------------------------------------------------------------------
# Queues
# ---------------------------------------------------------------------------
QUEUES = (
    Queue("default", default_exchange, routing_key="default"),
    Queue("io_heavy", io_exchange, routing_key="io_heavy"),
    Queue("cpu_heavy", cpu_exchange, routing_key="cpu_heavy"),
)

# ---------------------------------------------------------------------------
# Task → queue routing
# Prefix pattern:  app.tasks.<module>.<task_name>
# ---------------------------------------------------------------------------
TASK_ROUTES = {
    # IO-bound: network calls, API requests, DB writes
    "app.tasks.io.*": {"queue": "io_heavy", "routing_key": "io_heavy"},
    # CPU-bound: video rendering, audio processing, ML inference
    "app.tasks.cpu.*": {"queue": "cpu_heavy", "routing_key": "cpu_heavy"},
    # Everything else → default
    "app.tasks.*": {"queue": "default", "routing_key": "default"},
}

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
celery_app = Celery(
    "chitraai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.generate",
        "app.tasks.example",
    ],
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Queues & routing
    task_queues=QUEUES,
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
    task_routes=TASK_ROUTES,

    # Reliability
    task_track_started=True,
    task_acks_late=True,               # ack only after task completes
    task_reject_on_worker_lost=True,   # requeue if worker dies mid-task
    result_expires=3600,

    # Retry defaults (override per-task as needed)
    task_max_retries=3,
    task_default_retry_delay=10,       # seconds

    # Worker
    worker_prefetch_multiplier=1,      # fair dispatch — critical for long tasks
    worker_max_tasks_per_child=100,    # recycle worker after 100 tasks (memory safety)
)
