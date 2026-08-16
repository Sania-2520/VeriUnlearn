"""In-process background task runner.

Unlearning runs are dispatched as asyncio tasks and tracked by request id so
the API can return immediately and clients poll ``GET /unlearning/requests/{id}``.
Each task uses its own DB session (SQLAlchemy async sessions are not
shareable across tasks).
"""
from __future__ import annotations

import asyncio
import logging

from app.db.session import SessionLocal
from app.services.unlearning import UnlearningService

logger = logging.getLogger("veriunlearn.workers")

_tasks: dict[str, asyncio.Task] = {}


async def dispatch_unlearning(request_id: str) -> None:
    if request_id in _tasks and not _tasks[request_id].done():
        return
    task = asyncio.create_task(_run_unlearning(request_id))
    _tasks[request_id] = task


async def _run_unlearning(request_id: str) -> None:
    async with SessionLocal() as session:
        service = UnlearningService(session)
        await service.execute(request_id)
        await session.commit()


def task_status(request_id: str) -> str | None:
    task = _tasks.get(request_id)
    if task is None:
        return None
    if task.done():
        return "done" if not task.cancelled() and not task.exception() else "error"
    return "running"
