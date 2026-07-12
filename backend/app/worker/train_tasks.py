from __future__ import annotations

from typing import Any

from loguru import logger

from app.ml.model_manager import ModelManager
from app.ml.trainer import Trainer
from app.worker.celery_app import celery_app


@celery_app.task(bind=True, name="train_model")
def train_model_task(
    self,
    dataset_id: int,
    model_version_id: int | None = None,
    hyperparameters: dict | None = None,
) -> dict[str, Any]:
    task_id = self.request.id
    logger.info(f"Training task started: {task_id}, dataset={dataset_id}")

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

        self.update_state(state="PROGRESS", meta={"progress": 1.0, "status": "completed"})

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
        self.update_state(state="FAILURE", meta={"progress": 0.0, "status": "failed", "error": str(e)})
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

    from app.models.training import TrainingSample, TrainingDataset
    from sqlalchemy import create_engine, select

    db_path = "data/veriunlearn.db"

    engine = create_engine(f"sqlite:///{db_path}")
    from sqlalchemy.orm import Session
    with Session(engine) as session:
        result = session.execute(select(TrainingSample).where(TrainingSample.dataset_id == dataset_id))
        samples = result.scalars().all()

        from app.ml.model_manager import ModelManager
        model_mgr = ModelManager()

        import json as _json
        dataset_path = model_mgr.adapter_dir / f"dataset_{dataset_id}.json"
        sample_data = [
            {"role": "assistant", "content": s.content} for s in samples if s.content
        ]
        with open(dataset_path, "w") as f:
            _json.dump(sample_data, f)

        result = session.execute(select(TrainingDataset).where(TrainingDataset.id == dataset_id))
        dataset = result.scalar_one_or_none()
        if dataset:
            dataset.status = "ready"
            session.commit()

    engine.dispose()

    return {
        "task_id": task_id,
        "dataset_id": dataset_id,
        "status": "completed",
        "sample_count": len(samples),
    }
