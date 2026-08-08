from celery import Celery  # type: ignore[import-untyped]  # no stubs shipped
from celery.schedules import crontab  # type: ignore[import-untyped]  # no stubs shipped
from celery.signals import (  # type: ignore[import-untyped]  # no stubs shipped
    worker_process_shutdown,
    worker_shutdown,
)

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

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
    # Reliability: acknowledge tasks only after they complete so work is
    # redelivered (at-least-once) if a worker dies mid-task. Reject tasks on
    # worker loss so the broker requeues them, and cancel in-flight long
    # tasks when the connection drops to free up capacity promptly.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_cancel_long_running_tasks_on_connection_loss=True,
    broker_connection_retry_on_startup=True,
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


@worker_shutdown.connect
def on_worker_shutdown(**kwargs) -> None:
    """Release worker-owned resources on graceful shutdown."""
    try:
        from app.workers.session import _sync_engine
        _sync_engine.dispose()
        logger.info("Celery worker sync engine disposed")
    except Exception:
        logger.warning("Failed to dispose Celery worker sync engine", exc_info=True)


@worker_process_shutdown.connect
def on_worker_process_shutdown(**kwargs) -> None:
    """Release per-child-process resources on graceful shutdown.

    Each prefork child owns its own sync engine; disposing it in the parent
    (``worker_shutdown``) never reaches the children, so this hook disposes
    the engine inside each process that is being torn down.
    """
    try:
        from app.workers.session import _sync_engine
        _sync_engine.dispose()
        logger.info("Celery worker child process sync engine disposed")
    except Exception:
        logger.warning("Failed to dispose Celery worker child sync engine", exc_info=True)
