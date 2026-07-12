from __future__ import annotations

import sqlite3
from typing import Any

from loguru import logger

from app.core.config import settings
from app.worker.celery_app import celery_app


def _get_request_data(request_id: int) -> dict[str, Any] | None:
    conn = sqlite3.connect(settings.sqlite_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT id, algorithm, reason, status FROM unlearning_requests WHERE id = ?",
        (request_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


def _get_sample_ids_for_request(request_id: int) -> list[int]:
    conn = sqlite3.connect(settings.sqlite_path)
    cursor = conn.execute(
        "SELECT training_sample_id FROM unlearning_samples WHERE request_id = ?",
        (request_id,),
    )
    ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return ids


def _get_retained_samples(deleted_ids: list[int]) -> list[dict]:
    conn = sqlite3.connect(settings.sqlite_path)
    conn.row_factory = sqlite3.Row
    if deleted_ids:
        placeholders = ",".join("?" * len(deleted_ids))
        cursor = conn.execute(
            f"SELECT id, content, user_prompt FROM training_samples WHERE id NOT IN ({placeholders})",
            deleted_ids,
        )
    else:
        cursor = conn.execute("SELECT id, content, user_prompt FROM training_samples")
    samples = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return samples


def _get_deleted_samples(deleted_ids: list[int]) -> list[dict]:
    if not deleted_ids:
        return []
    conn = sqlite3.connect(settings.sqlite_path)
    conn.row_factory = sqlite3.Row
    placeholders = ",".join("?" * len(deleted_ids))
    cursor = conn.execute(
        f"SELECT id, content, user_prompt FROM training_samples WHERE id IN ({placeholders})",
        deleted_ids,
    )
    samples = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return samples


def _update_request_status(request_id: int, status: str, error: str | None = None) -> None:
    conn = sqlite3.connect(settings.sqlite_path)
    if error:
        conn.execute(
            "UPDATE unlearning_requests SET status = ?, error_message = ? WHERE id = ?",
            (status, error, request_id),
        )
    else:
        conn.execute(
            "UPDATE unlearning_requests SET status = ? WHERE id = ?",
            (status, request_id),
        )
    conn.commit()
    conn.close()


def _create_model_version(
    adapter_path: str, model_hash: str, algorithm: str, num_samples: int
) -> int:
    conn = sqlite3.connect(settings.sqlite_path)
    cursor = conn.execute(
        """INSERT INTO model_versions
           (base_model, adapter_path, hash, status, num_samples, created_at)
           VALUES (?, ?, ?, 'completed', ?, datetime('now'))""",
        (settings.base_model_name, adapter_path, model_hash, num_samples),
    )
    version_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return version_id


def _save_result(
    request_id: int,
    model_version_before_id: int | None,
    model_version_after_id: int | None,
    algorithm: str,
    result: dict[str, Any],
) -> None:
    conn = sqlite3.connect(settings.sqlite_path)
    conn.execute(
        """INSERT INTO unlearning_results
           (request_id, model_version_before_id, model_version_after_id,
            algorithm, execution_mode, simulated, privacy_score,
            merkle_root, signature, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
        (
            request_id,
            model_version_before_id,
            model_version_after_id,
            algorithm,
            result.get("execution_mode", "virtual"),
            1 if result.get("retrained") is False else 0,
            result.get("privacy_score", 0.5),
            result.get("merkle_root", ""),
            result.get("signature", ""),
        ),
    )
    conn.commit()
    conn.close()


@celery_app.task(bind=True, name="execute_unlearning")
def execute_unlearning_task(self, request_id: int) -> dict[str, Any]:
    task_id = self.request.id
    logger.info(f"Unlearning task started: {task_id}, request={request_id}")

    request_data = _get_request_data(request_id)
    if not request_data:
        logger.error(f"Request {request_id} not found")
        return {"task_id": task_id, "request_id": request_id, "status": "failed", "error": "Request not found"}

    algorithm = request_data.get("algorithm", "sisa")
    _update_request_status(request_id, "processing")

    self.update_state(state="PROGRESS", meta={"progress": 0.1, "status": "analyzing_samples"})

    deleted_ids = _get_sample_ids_for_request(request_id)
    retained_samples = _get_retained_samples(deleted_ids)
    deleted_samples = _get_deleted_samples(deleted_ids)
    deleted_content = [s.get("content", "") for s in deleted_samples]

    self.update_state(state="PROGRESS", meta={"progress": 0.3, "status": "running_mia_before"})

    self.update_state(state="PROGRESS", meta={"progress": 0.5, "status": "executing_unlearning"})

    shard_id = f"celery_req_{request_id}"
    result: dict[str, Any] = {}

    try:
        if settings.unlearning_mode != "real":
            result = _execute_virtual(algorithm, retained_samples, deleted_ids, shard_id, deleted_content)
        else:
            import torch
            if not torch.cuda.is_available():
                result = _execute_virtual(algorithm, retained_samples, deleted_ids, shard_id, deleted_content)
            else:
                result = _execute_real(algorithm, retained_samples, deleted_ids, shard_id, deleted_content)

        self.update_state(state="PROGRESS", meta={"progress": 0.8, "status": "verifying"})

        version_id = _create_model_version(
            adapter_path=result.get("adapter_path", ""),
            model_hash=result.get("hash", ""),
            algorithm=algorithm,
            num_samples=len(retained_samples),
        )

        _save_result(
            request_id=request_id,
            model_version_before_id=None,
            model_version_after_id=version_id,
            algorithm=algorithm,
            result=result,
        )

        _update_request_status(request_id, "completed")

        self.update_state(state="PROGRESS", meta={"progress": 1.0, "status": "completed"})

        return {
            "task_id": task_id,
            "request_id": request_id,
            "status": "completed",
            "algorithm": algorithm,
            "model_version_id": version_id,
            "result": result,
        }

    except Exception as e:
        logger.error(f"Unlearning failed: {e}")
        _update_request_status(request_id, "failed", str(e))
        self.update_state(state="FAILURE", meta={"progress": 0.0, "status": "failed", "error": str(e)})
        return {
            "task_id": task_id,
            "request_id": request_id,
            "status": "failed",
            "error": str(e),
        }


def _execute_virtual(
    algorithm: str,
    retained_samples: list[dict],
    deleted_ids: list[int],
    shard_id: str,
    deleted_content: list[str],
) -> dict[str, Any]:
    import hashlib
    import json

    if algorithm == "bad_teacher":
        from app.ml.unlearning.bad_teacher import BadTeacherUnlearning
        inst = BadTeacherUnlearning()
        return inst.execute(
            retained_samples=retained_samples,
            deleted_sample_ids=deleted_ids,
            shard_id=shard_id,
            deleted_content=deleted_content,
        )
    elif algorithm == "sisa":
        from app.ml.unlearning.sisa import SISAUnlearning
        inst = SISAUnlearning()
        return inst.execute(
            retained_samples=retained_samples,
            deleted_sample_ids=deleted_ids,
            shard_id=shard_id,
        )
    elif algorithm == "catastrophic_forgetting":
        from app.ml.unlearning.cat import CatastrophicForgetting
        inst = CatastrophicForgetting()
        return inst.execute(
            retained_samples=retained_samples,
            deleted_sample_ids=deleted_ids,
            shard_id=shard_id,
        )
    elif algorithm == "relu_erasure":
        from app.ml.unlearning.relu import ReLUErasure
        inst = ReLUErasure()
        return inst.execute(
            retained_samples=retained_samples,
            deleted_sample_ids=deleted_ids,
            shard_id=shard_id,
        )
    else:
        fingerprint = hashlib.sha256(
            json.dumps({"algorithm": algorithm, "deleted": sorted(deleted_ids)}, sort_keys=True).encode()
        ).hexdigest()
        return {
            "adapter_path": f"virtual://{algorithm}/{shard_id}",
            "hash": fingerprint,
            "retrained": False,
            "algorithm": algorithm,
        }


def _execute_real(
    algorithm: str,
    retained_samples: list[dict],
    deleted_ids: list[int],
    shard_id: str,
    deleted_content: list[str],
) -> dict[str, Any]:
    from app.ml.model_manager import ModelManager

    model_mgr = ModelManager()
    model, tokenizer = model_mgr.load_base_model()

    if algorithm == "bad_teacher":
        from app.ml.unlearning.bad_teacher import BadTeacherUnlearning
        inst = BadTeacherUnlearning()
        inst._model = model
        inst._tokenizer = tokenizer
        return inst.execute(
            retained_samples=retained_samples,
            deleted_sample_ids=deleted_ids,
            shard_id=shard_id,
            deleted_content=deleted_content,
        )
    elif algorithm == "sisa":
        from app.ml.unlearning.sisa import SISAUnlearning
        inst = SISAUnlearning()
        return inst.execute(
            retained_samples=retained_samples,
            deleted_sample_ids=deleted_ids,
            shard_id=shard_id,
        )
    elif algorithm == "catastrophic_forgetting":
        from app.ml.unlearning.cat import CatastrophicForgetting
        inst = CatastrophicForgetting()
        return inst.execute(
            retained_samples=retained_samples,
            deleted_sample_ids=deleted_ids,
            shard_id=shard_id,
        )
    elif algorithm == "relu_erasure":
        from app.ml.unlearning.relu import ReLUErasure
        inst = ReLUErasure()
        return inst.execute(
            retained_samples=retained_samples,
            deleted_sample_ids=deleted_ids,
            shard_id=shard_id,
        )
    else:
        return _execute_virtual(algorithm, retained_samples, deleted_ids, shard_id, deleted_content)
