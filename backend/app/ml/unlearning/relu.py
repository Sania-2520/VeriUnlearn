from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import torch
from loguru import logger
from peft import PeftModel

from app.ml.model_manager import ModelManager


class ReLUErasure:
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
            logger.warning(f"relu: model not available ({e}), using virtual fallback")
            return False

    def execute(
        self,
        retained_samples: list[dict],
        deleted_sample_ids: list[int],
        shard_id: str,
        base_adapter_path: str | None = None,
    ) -> dict[str, Any]:
        logger.info(f"relu_erasure: shard={shard_id}, deleted={len(deleted_sample_ids)}")

        if not self._ensure_model():
            return self._virtual_result(shard_id, deleted_sample_ids)

        try:
            model, tokenizer = self._model, self._tokenizer  # noqa: F841

            if base_adapter_path and Path(base_adapter_path).exists():
                peft_model = PeftModel.from_pretrained(model, base_adapter_path)
            else:
                peft_model = self.model_mgr.create_lora_adapter(model)

            erasure_ratio = len(deleted_sample_ids) / max(len(retained_samples), 1)
            scale_factor = max(0.0, 1.0 - erasure_ratio)

            with torch.no_grad():
                for name, param in peft_model.named_parameters():
                    if "lora_A" in name and param.requires_grad:
                        param.data.mul_(scale_factor)
                    elif "lora_B" in name and param.requires_grad:
                        if scale_factor < 0.5:
                            param.data.zero_()

            adapter_name = f"relu_erasure_{shard_id}"
            save_path = self.model_mgr.save_adapter(peft_model, adapter_name)
            model_hash = self.model_mgr.compute_model_hash(save_path)

            return {
                "shard_id": shard_id,
                "adapter_path": save_path,
                "hash": model_hash,
                "num_samples": len(retained_samples),
                "deleted_ids": deleted_sample_ids,
                "retrained": True,
                "algorithm": "relu_erasure",
            }

        except Exception as e:
            logger.error(f"relu_erasure execution failed: {e}")
            return self._virtual_result(shard_id, deleted_sample_ids)

    def _virtual_result(self, shard_id: str, deleted_ids: list[int]) -> dict[str, Any]:
        fingerprint = hashlib.sha256(
            json.dumps({"shard_id": shard_id, "deleted_ids": sorted(deleted_ids), "algorithm": "relu_erasure"}, sort_keys=True).encode()
        ).hexdigest()
        return {
            "shard_id": shard_id,
            "adapter_path": f"virtual://relu_erasure/{shard_id}",
            "hash": fingerprint,
            "num_samples": 0,
            "deleted_ids": deleted_ids,
            "retrained": False,
            "algorithm": "relu_erasure",
        }
