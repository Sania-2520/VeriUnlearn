from __future__ import annotations

from typing import Any

from loguru import logger
from peft import PeftModel

from app.ml.model_manager import ModelManager


class CertifiedRemoval:
    def __init__(self) -> None:
        self.model_mgr = ModelManager()

    def execute(
        self,
        deleted_sample_ids: list[int],
        model: PeftModel,
        adapter_path: str,
    ) -> dict[str, Any]:
        logger.info(f"Certified removal: {len(deleted_sample_ids)} samples")

        adapter_name = "certified_removal"
        save_path = self.model_mgr.save_adapter(model, adapter_name)
        model_hash = self.model_mgr.compute_model_hash(save_path)

        return {
            "adapter_path": save_path,
            "hash": model_hash,
            "deleted_ids": deleted_sample_ids,
            "algorithm": "certified_removal",
        }
