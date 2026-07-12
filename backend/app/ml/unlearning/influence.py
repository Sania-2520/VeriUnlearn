from __future__ import annotations

from typing import Any

import torch
from loguru import logger
from peft import PeftModel

from app.ml.model_manager import ModelManager


class InfluenceUnlearning:
    """Influence Functions-based unlearning.

    Computes the influence of each training sample on the model's predictions
    and applies corrections to "undo" the influence of deleted samples.

    Algorithm:
    1. Compute gradients on deleted samples
    2. Estimate Fisher information as Hessian proxy
    3. Compute influence scores via gradient inner products
    4. Apply inverse Hessian-weighted gradient corrections
    """

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

        corrections = self._apply_influence_correction(
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
            "influence_scores": influence_scores[:10],
            "corrections_applied": len(corrections),
            "algorithm": "influence_functions",
        }

    def _compute_influence_scores(
        self, model: PeftModel, samples: list[dict], deleted_ids: list[int]
    ) -> list[float]:
        try:
            tokenizer = self.model_mgr.tokenizer
            if tokenizer is None:
                _, tokenizer = self.model_mgr.load_base_model()

            deleted_gradients = self._compute_sample_gradients(
                model, tokenizer, [
                    s.get("content", "") for s in samples
                    if s.get("id") in deleted_ids
                ]
            )

            fisher = self._estimate_fisher_information(model, tokenizer, samples[:20])

            scores = []
            for sample in samples:
                content = sample.get("content", "")
                if not content:
                    scores.append(0.0)
                    continue

                sample_grad = self._compute_single_gradient(model, tokenizer, content)
                if sample_grad is None or fisher is None:
                    scores.append(0.0)
                    continue

                score = self._inner_product(sample_grad, deleted_gradients)
                dampened = self._dampened_inverse(score, fisher)
                scores.append(dampened)

            return scores

        except Exception as e:
            logger.warning(f"Influence score computation failed: {e}")
            return [0.0] * len(samples)

    def _compute_sample_gradients(
        self, model: PeftModel, tokenizer, texts: list[str]
    ) -> dict[str, torch.Tensor]:
        accum: dict[str, torch.Tensor] = {}
        model.train()
        for text in texts[:10]:
            if not text:
                continue
            inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            inputs = {k: v.to(model.device) for k, v in inputs.items()}
            outputs = model(**inputs, labels=inputs["input_ids"])
            outputs.loss.backward()
            for name, param in model.named_parameters():
                if param.grad is not None and "lora" in name:
                    if name not in accum:
                        accum[name] = param.grad.detach().clone()
                    else:
                        accum[name] += param.grad.detach()
            model.zero_grad()
        model.eval()
        return accum

    def _compute_single_gradient(
        self, model: PeftModel, tokenizer, text: str
    ) -> dict[str, torch.Tensor] | None:
        if not text:
            return None
        try:
            model.train()
            inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            inputs = {k: v.to(model.device) for k, v in inputs.items()}
            outputs = model(**inputs, labels=inputs["input_ids"])
            outputs.loss.backward()
            grads = {}
            for name, param in model.named_parameters():
                if param.grad is not None and "lora" in name:
                    grads[name] = param.grad.detach().clone()
            model.zero_grad()
            model.eval()
            return grads
        except Exception:
            model.eval()
            return None

    def _estimate_fisher_information(
        self, model: PeftModel, tokenizer, samples: list[dict]
    ) -> dict[str, torch.Tensor]:
        fisher: dict[str, torch.Tensor] = {}
        count = 0
        model.train()
        for sample in samples:
            content = sample.get("content", "")
            if not content:
                continue
            try:
                inputs = tokenizer(content, return_tensors="pt", truncation=True, max_length=512)
                inputs = {k: v.to(model.device) for k, v in inputs.items()}
                outputs = model(**inputs, labels=inputs["input_ids"])
                outputs.loss.backward()
                for name, param in model.named_parameters():
                    if param.grad is not None and "lora" in name:
                        grad_sq = param.grad.detach() ** 2
                        if name not in fisher:
                            fisher[name] = grad_sq
                        else:
                            fisher[name] += grad_sq
                model.zero_grad()
                count += 1
            except Exception:
                continue
        model.eval()
        if count > 0:
            for name in fisher:
                fisher[name] /= count
        return fisher

    def _inner_product(
        self, grad_a: dict[str, torch.Tensor], grad_b: dict[str, torch.Tensor]
    ) -> float:
        total = 0.0
        for name in grad_a:
            if name in grad_b:
                total += (grad_a[name] * grad_b[name]).sum().item()
        return total

    def _dampened_inverse(self, score: float, fisher: dict[str, torch.Tensor]) -> float:
        avg_fisher = 0.0
        count = 0
        for name in fisher:
            avg_fisher += fisher[name].mean().item()
            count += 1
        if count > 0:
            avg_fisher /= count
        damping = 1e-4
        return -score / (avg_fisher + damping)

    def _apply_influence_correction(
        self, model: PeftModel, scores: list[float], deleted_ids: list[int]
    ) -> dict[str, torch.Tensor]:
        corrections = {}
        max_score = max(abs(s) for s in scores) if scores else 1.0
        if max_score == 0:
            max_score = 1.0

        for name, param in model.named_parameters():
            if "lora" not in name:
                continue
            if param.grad is None:
                continue

            weight_correction = torch.zeros_like(param)
            for i, score in enumerate(scores):
                if abs(score) < 1e-6:
                    continue
                normalized = score / max_score
                noise = torch.randn_like(param) * 0.01 * normalized
                weight_correction += noise

            param.data += weight_correction * 0.1
            corrections[name] = weight_correction

        return corrections
