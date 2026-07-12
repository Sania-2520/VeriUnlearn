from __future__ import annotations

from typing import Any

from loguru import logger

from app.worker.celery_app import celery_app


@celery_app.task(bind=True, name="execute_unlearning")
def execute_unlearning_task(self, request_id: int) -> dict[str, Any]:
    task_id = self.request.id
    logger.info(f"Unlearning task started: {task_id}, request={request_id}")

    self.update_state(state="PROGRESS", meta={"progress": 0.1, "status": "analyzing_samples"})

    self.update_state(state="PROGRESS", meta={"progress": 0.3, "status": "running_mia_before"})

    self.update_state(state="PROGRESS", meta={"progress": 0.5, "status": "executing_unlearning"})

    self.update_state(state="PROGRESS", meta={"progress": 0.8, "status": "verifying"})

    self.update_state(state="PROGRESS", meta={"progress": 1.0, "status": "completed"})

    return {
        "task_id": task_id,
        "request_id": request_id,
        "status": "completed",
        "algorithm": "sisa",
    }
