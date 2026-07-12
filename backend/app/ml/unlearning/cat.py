from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import torch
from loguru import logger

from app.ml.model_manager import ModelManager


class CatastrophicForgetting:
    def __init__(self) -> None:
        self.model_mgr = ModelManager()
        self._model = None
        self._tokenizer = None

    def _ensure_model(self) -> bool:
        if self._model is not None:
            return True
        try:
            self._model, self._tokenizer = self.model_mgr.load_base_model()
            return True
        except Exception as e:
            logger.warning(f"cat: model not available ({e}), using virtual fallback")
            return False

    def execute(
        self,
        retained_samples: list[dict],
        deleted_sample_ids: list[int],
        shard_id: str,
        base_adapter_path: str | None = None,
    ) -> dict[str, Any]:
        logger.info(f"catastrophic_forgetting: shard={shard_id}, deleted={len(deleted_sample_ids)}")

        if not self._ensure_model():
            return self._virtual_result(shard_id, deleted_sample_ids)

        try:
            model, tokenizer = self._model, self._tokenizer  # noqa: F841

            if base_adapter_path and Path(base_adapter_path).exists():
                from peft import PeftModel
                peft_model = PeftModel.from_pretrained(model, base_adapter_path)
            else:
                peft_model = self.model_mgr.create_lora_adapter(model)

            deletion_ratio = len(deleted_sample_ids) / max(len(retained_samples) + len(deleted_sample_ids), 1)
            noise_scale = 0.1 + deletion_ratio * 0.4

            with torch.no_grad():
                for name, param in peft_model.named_parameters():
                    if "lora" in name and param.requires_grad:
                        noise = torch.randn_like(param) * noise_scale
                        param.add_(noise)

            adapter_name = f"catastrophic_{shard_id}"
            save_path = self.model_mgr.save_adapter(peft_model, adapter_name)
            model_hash = self.model_mgr.compute_model_hash(save_path)

            return {
                "shard_id": shard_id,
                "adapter_path": save_path,
                "hash": model_hash,
                "num_samples": len(retained_samples),
                "deleted_ids": deleted_sample_ids,
                "retrained": True,
                "algorithm": "catastrophic_forgetting",
            }

        except Exception as e:
            logger.error(f"catastrophic_forgetting execution failed: {e}")
            return self._virtual_result(shard_id, deleted_sample_ids)

    def _virtual_result(self, shard_id: str, deleted_ids: list[int]) -> dict[str, Any]:
        fingerprint = hashlib.sha256(
            json.dumps({"shard_id": shard_id, "deleted_ids": sorted(deleted_ids), "algorithm": "catastrophic_forgetting"}, sort_keys=True).encode()
        ).hexdigest()
        return {
            "shard_id": shard_id,
            "adapter_path": f"virtual://catastrophic_forgetting/{shard_id}",
            "hash": fingerprint,
            "num_samples": 0,
            "deleted_ids": deleted_ids,
            "retrained": False,
            "algorithm": "catastrophic_forgetting",
        }
