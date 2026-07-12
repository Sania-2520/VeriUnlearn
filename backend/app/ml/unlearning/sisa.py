from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger
from peft import PeftModel

from app.ml.model_manager import ModelManager
from app.ml.trainer import Trainer


class SISAUnlearning:
    def __init__(self) -> None:
        self.model_mgr = ModelManager()
        self.trainer = Trainer()

    def execute(
        self,
        retained_samples: list[dict],
        deleted_sample_ids: list[int],
        shard_id: str,
        base_adapter_path: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        logger.info(f"SISA unlearning: shard={shard_id}, deleted={len(deleted_sample_ids)}, retained={len(retained_samples)}")

        model, tokenizer = self.model_mgr.load_base_model()

        if base_adapter_path and Path(base_adapter_path).exists():
            peft_model = PeftModel.from_pretrained(model, base_adapter_path)
            logger.info(f"Loaded existing adapter from {base_adapter_path}")
        else:
            peft_model = self.model_mgr.create_lora_adapter(model)

        if len(retained_samples) == 0:
            logger.warning("No retained samples — returning empty adapter")

            adapter_name = f"sisa_retrained_{shard_id}_empty"
            save_path = self.model_mgr.save_adapter(peft_model, adapter_name)
            model_hash = self.model_mgr.compute_model_hash(save_path)

            return {
                "shard_id": shard_id,
                "adapter_path": save_path,
                "hash": model_hash,
                "num_samples": 0,
                "deleted_ids": deleted_sample_ids,
                "retrained": True,
            }

        dataset = self.trainer.prepare_dataset(retained_samples, tokenizer)

        metrics = self.trainer.train(dataset, peft_model, tokenizer)

        adapter_name = f"sisa_retrained_{shard_id}"
        save_path = self.model_mgr.save_adapter(peft_model, adapter_name)
        model_hash = self.model_mgr.compute_model_hash(save_path)

        logger.info(f"SISA unlearning completed for shard {shard_id}")
        return {
            "shard_id": shard_id,
            "adapter_path": save_path,
            "hash": model_hash,
            "num_samples": len(retained_samples),
            "deleted_ids": deleted_sample_ids,
            "retrained": True,
            "train_loss": metrics.get("train_loss"),
        }
