import logging
import time
import uuid
from typing import Any, Optional

import numpy as np
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class CounterfactualExplainer:
    def __init__(self, model: Optional[nn.Module] = None, feature_names: Optional[list[str]] = None):
        self.model = model
        self.feature_names = feature_names or [f"feat_{i}" for i in range(10)]

    def set_model(self, model: nn.Module) -> None:
        self.model = model
        self.model.eval()

    def generate(
        self,
        input_sample: np.ndarray,
        target_class: int,
        num_steps: int = 500,
        lr: float = 0.01,
        distance_weight: float = 0.5,
        feature_mask: Optional[list[int]] = None,
        epsilon: float = 1e-6,
    ) -> dict[str, Any]:
        if self.model is None:
            return {"error": "No model set"}

        input_tensor = torch.from_numpy(input_sample.astype(np.float32)).unsqueeze(0)
        input_tensor.requires_grad_(True)

        optimizer = torch.optim.Adam([input_tensor], lr=lr)
        target_tensor = torch.tensor([target_class])

        original = input_tensor.detach().clone()
        best_cf = None
        best_loss = float("inf")
        history = []

        start_time = time.perf_counter()

        for step in range(num_steps):
            optimizer.zero_grad()
            output = self.model(input_tensor)
            pred = output.argmax(dim=1).item()

            ce_loss = nn.functional.cross_entropy(output, target_tensor)
            l2_dist = torch.sum((input_tensor - original) ** 2)

            if feature_mask is not None:
                mask_tensor = torch.zeros_like(input_tensor)
                mask_tensor[0, feature_mask] = 1.0
                l2_dist = torch.sum(((input_tensor - original) * mask_tensor) ** 2)

            loss = ce_loss + distance_weight * l2_dist
            loss.backward()
            optimizer.step()

            with torch.no_grad():
                input_tensor.data.clamp_(-10.0, 10.0)

            history.append({
                "step": step,
                "loss": loss.item(),
                "ce_loss": ce_loss.item(),
                "l2_dist": l2_dist.item(),
                "predicted_class": pred,
            })

            if pred == target_class and loss.item() < best_loss:
                best_loss = loss.item()
                best_cf = input_tensor.detach().clone()

            if pred == target_class and l2_dist.item() < epsilon:
                break

        elapsed = (time.perf_counter() - start_time) * 1000

        if best_cf is not None:
            cf_array = best_cf.squeeze(0).numpy()
            delta = cf_array - input_sample
            return {
                "success": True,
                "counterfactual": cf_array.tolist(),
                "delta": delta.tolist(),
                "delta_norm": float(np.linalg.norm(delta)),
                "original_class": int(output.argmax(dim=1).item()),
                "target_class": target_class,
                "steps": step + 1,
                "runtime_ms": round(elapsed, 2),
                "feature_perturbations": {
                    self.feature_names[i] if i < len(self.feature_names) else f"feat_{i}": {
                        "original": float(input_sample[i]),
                        "counterfactual": float(cf_array[i]),
                        "change": float(delta[i]),
                    }
                    for i in range(min(len(input_sample), len(self.feature_names)))
                },
                "history": history[:10],
            }
        return {
            "success": False,
            "message": "Could not find counterfactual within step limit",
            "steps": num_steps,
            "runtime_ms": round(elapsed, 2),
        }

    def generate_batch(
        self,
        samples: list[np.ndarray],
        target_class: int = 0,
        **kwargs,
    ) -> list[dict[str, Any]]:
        return [self.generate(s, target_class, **kwargs) for s in samples]

    @staticmethod
    def compute_minimum_distance(
        cf_result: dict[str, Any],
        reference_samples: list[np.ndarray],
    ) -> float:
        if not cf_result.get("success"):
            return float("inf")
        cf = np.array(cf_result["counterfactual"])
        min_dist = float("inf")
        for ref in reference_samples:
            dist = np.linalg.norm(cf - ref)
            min_dist = min(min_dist, dist)
        return float(min_dist)

    @staticmethod
    def plausibility_score(
        cf_result: dict[str, Any],
        data_distribution: np.ndarray,
    ) -> float:
        if not cf_result.get("success"):
            return 0.0
        cf = np.array(cf_result["counterfactual"])
        mean = data_distribution.mean(axis=0)
        std = data_distribution.std(axis=0) + 1e-8
        z_scores = np.abs((cf - mean) / std)
        return float(np.clip(1.0 - z_scores.mean() / 3.0, 0.0, 1.0))
