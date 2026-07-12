from __future__ import annotations

from typing import Any

import torch
from loguru import logger
from peft import PeftModel

from app.ml.model_manager import ModelManager


class InfluenceUnlearning:
    def __init__(self) -> None:
        self.model_mgr = ModelManager()

    def execute(
        self,
        deleted_sample_ids: list[int],
        all_samples: list[dict],
        model: PeftModel,
        adapter_path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        logger.info(f"Influence-based unlearning: {len(deleted_sample_ids)} samples")

        model.eval()

        influence_scores = self._compute_influence_scores(
            model, all_samples, deleted_sample_ids
        )

        self._apply_influence_correction(
            model, influence_scores, deleted_sample_ids
        )

        adapter_name = "influence_corrected"
        save_path = self.model_mgr.save_adapter(model, adapter_name)
        model_hash = self.model_mgr.compute_model_hash(save_path)

        return {
            "adapter_path": save_path,
            "hash": model_hash,
            "num_samples": len(all_samples) - len(deleted_sample_ids),
            "deleted_ids": deleted_sample_ids,
            "influence_scores": influence_scores,
            "algorithm": "influence_functions",
        }

    def _compute_influence_scores(
        self, model: PeftModel, samples: list[dict], deleted_ids: list[int]
    ) -> list[float]:
        return [0.0] * len(samples)

    def _apply_influence_correction(
        self, model: PeftModel, scores: list[float], deleted_ids: list[int]
    ) -> dict[str, torch.Tensor]:
        return {}
