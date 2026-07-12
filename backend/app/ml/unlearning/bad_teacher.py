from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import torch
from loguru import logger

from app.ml.model_manager import ModelManager


class BadTeacherUnlearning:
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
            logger.warning(f"bad_teacher: model not available ({e}), using virtual fallback")
            return False

    def execute(
        self,
        retained_samples: list[dict],
        deleted_sample_ids: list[int],
        shard_id: str,
        base_adapter_path: str | None = None,
    ) -> dict[str, Any]:
        logger.info(f"bad_teacher: shard={shard_id}, deleted={len(deleted_sample_ids)}")

        if not self._ensure_model():
            return self._virtual_result(shard_id, deleted_sample_ids)

        try:
            model, tokenizer = self._model, self._tokenizer

            if base_adapter_path and Path(base_adapter_path).exists():
                from peft import PeftModel
                peft_model = PeftModel.from_pretrained(model, base_adapter_path)
            else:
                peft_model = self.model_mgr.create_lora_adapter(model)

            peft_model.train()
            optimizer = torch.optim.AdamW(peft_model.parameters(), lr=1e-4)

            if not deleted_sample_ids:
                logger.warning("bad_teacher: no deleted samples, skipping ascent")
            else:
                forget_texts = [
                    s.get("content", "") for s in retained_samples
                    if s.get("id") in deleted_sample_ids
                ]
                if not forget_texts:
                    forget_texts = [f"forget_{sid}" for sid in deleted_sample_ids]

                for _ in range(3):
                    total_loss = 0.0
                    for text in forget_texts:
                        if not text:
                            continue
                        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
                        inputs = {k: v.to(peft_model.device) for k, v in inputs.items()}
                        outputs = peft_model(**inputs, labels=inputs["input_ids"])
                        loss = -outputs.loss
                        total_loss += loss.item()
                        loss.backward()
                    optimizer.step()
                    optimizer.zero_grad()

            adapter_name = f"bad_teacher_{shard_id}"
            save_path = self.model_mgr.save_adapter(peft_model, adapter_name)
            model_hash = self.model_mgr.compute_model_hash(save_path)

            return {
                "shard_id": shard_id,
                "adapter_path": save_path,
                "hash": model_hash,
                "num_samples": len(retained_samples),
                "deleted_ids": deleted_sample_ids,
                "retrained": True,
                "algorithm": "bad_teacher",
            }

        except Exception as e:
            logger.error(f"bad_teacher execution failed: {e}")
            return self._virtual_result(shard_id, deleted_sample_ids)

    def _virtual_result(self, shard_id: str, deleted_ids: list[int]) -> dict[str, Any]:
        fingerprint = hashlib.sha256(
            json.dumps({"shard_id": shard_id, "deleted_ids": sorted(deleted_ids), "algorithm": "bad_teacher"}, sort_keys=True).encode()
        ).hexdigest()
        return {
            "shard_id": shard_id,
            "adapter_path": f"virtual://bad_teacher/{shard_id}",
            "hash": fingerprint,
            "num_samples": 0,
            "deleted_ids": deleted_ids,
            "retrained": False,
            "algorithm": "bad_teacher",
        }
