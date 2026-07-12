from __future__ import annotations

import sqlite3
from typing import Any

from loguru import logger

from app.core.config import settings
from app.ml.model_manager import ModelManager
from app.ml.trainer import Trainer
from app.worker.celery_app import celery_app

try:
    from app.metrics import TRAINING_JOBS_TOTAL, TRAINING_DURATION
except ImportError:
    TRAINING_JOBS_TOTAL = None
    TRAINING_DURATION = None


def _update_model_version(
    model_version_id: int,
    adapter_path: str | None = None,
    model_hash: str | None = None,
    status: str | None = None,
    num_samples: int | None = None,
    train_loss: float | None = None,
) -> None:
    conn = sqlite3.connect(settings.sqlite_path)
    sets: list[str] = []
    params: list[Any] = []
    if adapter_path is not None:
        sets.append("adapter_path = ?")
        params.append(adapter_path)
    if model_hash is not None:
        sets.append("hash = ?")
        params.append(model_hash)
    if status is not None:
        sets.append("status = ?")
        params.append(status)
    if num_samples is not None:
        sets.append("num_samples = ?")
        params.append(num_samples)
    if train_loss is not None:
        sets.append("train_loss = ?")
        params.append(train_loss)
    if sets:
        params.append(model_version_id)
        conn.execute(f"UPDATE model_versions SET {', '.join(sets)} WHERE id = ?", params)
        conn.commit()
    conn.close()


@celery_app.task(bind=True, name="train_model")
def train_model_task(
    self,
    dataset_id: int,
    model_version_id: int | None = None,
    hyperparameters: dict | None = None,
) -> dict[str, Any]:
    task_id = self.request.id
    logger.info(f"Training task started: {task_id}, dataset={dataset_id}")

    import time
    start_time = time.time()

    self.update_state(state="PROGRESS", meta={"progress": 0.0, "status": "preparing_dataset"})

    try:
        self.update_state(state="PROGRESS", meta={"progress": 0.1, "status": "loading_model"})

        model_mgr = ModelManager()
        trainer = Trainer()

        model, tokenizer = model_mgr.load_base_model()

        self.update_state(state="PROGRESS", meta={"progress": 0.2, "status": "creating_adapter"})

        peft_model = model_mgr.create_lora_adapter(model)

        self.update_state(state="PROGRESS", meta={"progress": 0.3, "status": "building_dataset"})

        import json as _json
        from pathlib import Path
        dataset_path = Path(model_mgr.adapter_dir) / f"dataset_{dataset_id}.json"
        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

        with open(dataset_path) as f:
            samples = _json.load(f)

        hf_dataset = trainer.prepare_dataset(samples, tokenizer)

        self.update_state(state="PROGRESS", meta={"progress": 0.4, "status": "training"})

        metrics = trainer.train(
            hf_dataset,
            peft_model,
            tokenizer,
            callbacks={
                "on_step": lambda m: self.update_state(
                    state="PROGRESS",
                    meta={
                        "progress": 0.4 + 0.5 * (m["epoch"] - 1 + m["step"] / 100) / 3,
                        "status": "training",
                        "current_loss": m["loss"],
                        "current_epoch": m["epoch"],
                        "total_epochs": 3,
                    },
                )
            },
        )

        self.update_state(state="PROGRESS", meta={"progress": 0.9, "status": "saving_model"})

        adapter_name = f"model_v{model_version_id or dataset_id}"
        save_path = model_mgr.save_adapter(peft_model, adapter_name)
        model_hash = model_mgr.compute_model_hash(save_path)

        if model_version_id is not None:
            _update_model_version(
                model_version_id,
                adapter_path=save_path,
                model_hash=model_hash,
                status="completed",
                num_samples=len(samples),
                train_loss=metrics.get("train_loss", 0.0),
            )

            try:
                from app.services.webhook_service import webhook_service
                import asyncio
                asyncio.get_event_loop().run_until_complete(
                    webhook_service.dispatch("training.completed", {
                        "model_version_id": model_version_id,
                        "dataset_id": dataset_id,
                        "adapter_path": save_path,
                        "model_hash": model_hash,
                        "train_loss": metrics.get("train_loss", 0.0),
                        "num_samples": len(samples),
                    })
                )
            except Exception as e:
                logger.warning(f"Webhook dispatch failed: {e}")

        self.update_state(state="PROGRESS", meta={"progress": 1.0, "status": "completed"})

        duration = time.time() - start_time
        if TRAINING_JOBS_TOTAL:
            TRAINING_JOBS_TOTAL.labels(status="completed").inc()
        if TRAINING_DURATION:
            TRAINING_DURATION.observe(duration)

        return {
            "task_id": task_id,
            "dataset_id": dataset_id,
            "model_version_id": model_version_id,
            "status": "completed",
            "adapter_path": save_path,
            "model_hash": model_hash,
            "train_loss": metrics.get("train_loss", 0.0),
            "eval_loss": None,
            "num_samples": len(samples),
        }

    except Exception as e:
        logger.error(f"Training failed: {e}")

        if model_version_id is not None:
            _update_model_version(model_version_id, status="failed")

            try:
                from app.services.webhook_service import webhook_service
                import asyncio
                asyncio.get_event_loop().run_until_complete(
                    webhook_service.dispatch("training.failed", {
                        "model_version_id": model_version_id,
                        "dataset_id": dataset_id,
                        "error": str(e),
                    })
                )
            except Exception:
                pass

        self.update_state(state="FAILURE", meta={"progress": 0.0, "status": "failed", "error": str(e)})

        if TRAINING_JOBS_TOTAL:
            TRAINING_JOBS_TOTAL.labels(status="failed").inc()

        return {
            "task_id": task_id,
            "dataset_id": dataset_id,
            "model_version_id": model_version_id,
            "status": "failed",
            "error": str(e),
        }


@celery_app.task(bind=True, name="build_dataset")
def build_dataset_task(self, dataset_id: int) -> dict[str, Any]:
    task_id = self.request.id
    logger.info(f"Dataset build task started: {task_id}, dataset={dataset_id}")

    conn = sqlite3.connect(settings.sqlite_path)
    cursor = conn.execute(
        "SELECT id, conversation_id, message_id, user_id, content, user_prompt "
        "FROM training_samples WHERE dataset_id = ? AND user_prompt IS NOT NULL",
        (dataset_id,),
    )
    rows = cursor.fetchall()
    conn.close()

    from pathlib import Path
    adapter_dir = Path(settings.adapter_dir)
    adapter_dir.mkdir(parents=True, exist_ok=True)

    import json as _json
    dataset_path = adapter_dir / f"dataset_{dataset_id}.json"

    sample_data = []
    for row in rows:
        user_prompt = row[5]
        assistant_content = row[4]
        if user_prompt:
            sample_data.append({"role": "user", "content": user_prompt})
        sample_data.append({"role": "assistant", "content": assistant_content})

    with open(dataset_path, "w", encoding="utf-8") as f:
        _json.dump(sample_data, f, indent=2, ensure_ascii=False)

    conn = sqlite3.connect(settings.sqlite_path)
    conn.execute(
        "UPDATE training_datasets SET status = 'ready' WHERE id = ?", (dataset_id,)
    )
    conn.commit()
    conn.close()

    return {
        "task_id": task_id,
        "dataset_id": dataset_id,
        "status": "completed",
        "sample_count": len(rows),
    }
