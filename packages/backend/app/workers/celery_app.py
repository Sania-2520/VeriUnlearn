from celery import Celery  # type: ignore[import-untyped]  # no stubs shipped
from celery.schedules import crontab  # type: ignore[import-untyped]  # no stubs shipped

from app.core.config import settings

celery_app = Celery(
    "veriunlearn",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.unlearning_tasks",
        "app.workers.rag_tasks",
        "app.workers.notification_tasks",
        "app.workers.audit_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.unlearning_worker_timeout,
    task_soft_time_limit=settings.unlearning_worker_timeout - 30,
    worker_max_tasks_per_child=1000,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    beat_schedule={
        "retry-failed-webhooks": {
            "task": "notification.retry_failed_webhooks",
            "schedule": crontab(minute="*/5"),
            "options": {"expires": 240},
        },
        "cleanup-deletion-queue": {
            "task": "unlearning.cleanup_queue",
            "schedule": crontab(minute="*/30"),
            "options": {"expires": 1200},
        },
        "anchor-audit-chains": {
            "task": "audit.anchor_chains",
            "schedule": crontab(hour="*/6"),
            "options": {"expires": 3600},
        },
    },
)
