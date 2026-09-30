"""
Celery configuration for background render tasks.
"""

from celery import Celery
from celery.signals import worker_init, worker_shutdown

from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "ai_video_director",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.render_tasks",
    ],
)

# Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=7200,  # 2 hours max
    task_soft_time_limit=6600,  # 1h 50m soft limit
    worker_prefetch_multiplier=1,  # One task at a time for render workers
    worker_max_tasks_per_child=10,  # Restart worker after 10 tasks
    result_expires=86400,  # Results expire after 24 hours
    broker_connection_retry_on_startup=True,
)

# Task routes
celery_app.conf.task_routes = {
    "app.workers.render_tasks.render_preview_job": {"queue": "rendering"},
    "app.workers.render_tasks.render_export_job": {"queue": "rendering"},
}


@worker_init.connect
def init_worker(**kwargs):
    """Initialize worker resources."""
    ...


@worker_shutdown.connect
def shutdown_worker(**kwargs):
    """Cleanup worker resources."""
    ...
