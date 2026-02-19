import os
from celery import Celery
from celery.schedules import crontab

# Redis URL for broker and result backend
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "autograder",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks"],  # Auto-discover tasks from this module
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max for any task
    task_soft_time_limit=540,  # Warning at 9 minutes
    worker_prefetch_multiplier=1,  # Process one task at a time per worker
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks to prevent memory leaks
)

celery_app.conf.beat_schedule = {
    "hotmart-sync-hourly": {
        "task": "sync_hotmart_students",
        "schedule": crontab(minute=0),  # every hour on the hour
        "args": [],
    },
    "manychat-tag-sync-daily": {
        "task": "sync_manychat_tags",
        "schedule": crontab(hour=2, minute=0),  # 02:00 UTC daily
        "args": [],
    },
}
