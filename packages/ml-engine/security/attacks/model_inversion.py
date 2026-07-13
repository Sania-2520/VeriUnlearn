import math
import logging
from typing import Optional

import torch
from torch import Tensor, nn
from torch.optim import Adam

from models.single_model import SingleModel
from models.sharded_classifier import ShardedModel
from training.data import Dataset

logger = logging.getLogger(__name__)


class ModelInversionAttack:
    def __init__(
        self,
        learning_rate: float = 0.1,
        iterations: int = 1000,
        l1_reg: float = 0.0,
        l2_reg: float = 1e-3,
        device: Optional[torch.device] = None,
    ):
        self.learning_rate = learning_rate
        self.iterations = iterations
        self.l1_reg = l1_reg
        self.l2_reg = l2_reg
        self.device = device or torch.device("cpu")

    def reconstruct(
        self,
        model: SingleModel | ShardedModel,
        target_class: int,
        num_samples: int = 1,
        input_dim: Optional[int] = None,
        seed: Optional[Tensor] = None,
    ) -> Tensor:
        if input_dim is None:
            if isinstance(model, SingleModel):
                input_dim = model.input_dim
            else:
                input_dim = model.input_dim

        if seed is not None:
            x = seed.clone().detach().to(self.device).requires_grad_(True)
        else:
            x = torch.randn(num_samples, input_dim, device=self.device, requires_grad=True)

        optimizer = Adam([x], lr=self.learning_rate)

        target = torch.full((num_samples,), target_class, dtype=torch.long, device=self.device)

        for i in range(self.iterations):
            optimizer.zero_grad()

            if isinstance(model, SingleModel):
                logits = model.model(x)
            else:
                model_models = model.models
                all_logits = []
                for shard_model in model_models:
                    shard_model.eval()
                    all_logits.append(shard_model(x).unsqueeze(0))
                stacked = torch.cat(all_logits, dim=0)
                logits = stacked.mean(dim=0)

            loss_ce = nn.CrossEntropyLoss()(logits, target)

            loss_reg = torch.zeros(1, device=self.device)
            if self.l2_reg > 0:
                loss_reg = loss_reg + self.l2_reg * torch.norm(x.view(num_samples, -1), dim=1).mean()
            if self.l1_reg > 0:
                loss_reg = loss_reg + self.l1_reg * torch.norm(x.view(num_samples, -1), p=1, dim=1).mean()

            loss = loss_ce + loss_reg
            loss.backward()
            optimizer.step()

            x.data = torch.clamp(x.data, -10.0, 10.0)

        return x.detach()

    def attack(
        self,
        model: SingleModel | ShardedModel,
        target_classes: list[int],
        original_dataset: Optional[Dataset] = None,
    ) -> dict:
        results = []
        ssim_scores = []
        mse_scores = []
        confidence_scores = []

        for tc in target_classes:
            reconstructed = self.reconstruct(
                model=model,
                target_class=tc,
                num_samples=1,
            )

            if isinstance(model, SingleModel):
                logits = model.predict_logits(reconstructed)
            else:
                logits = model.predict_logits(reconstructed)
            probs = logits.softmax(dim=-1)
            confidence = probs[0, tc].item()
            confidence_scores.append(confidence)

            result_entry = {
                "target_class": tc,
                "reconstructed_sample": reconstructed.cpu().numpy().tolist()[0],
                "confidence": confidence,
            }

            if original_dataset is not None:
                class_indices = [
                    i for i in range(original_dataset.size)
                    if original_dataset.labels[i].item() == tc
                ]
                if class_indices:
                    orig_samples = original_dataset.features[class_indices].to(self.device)
                    rep = reconstructed.expand_as(orig_samples[:1])

                    mse = nn.functional.mse_loss(rep, orig_samples[:1]).item()
                    mse_scores.append(mse)

                    cos_sim = nn.functional.cosine_similarity(
                        rep.view(1, -1), orig_samples[:1].view(1, -1)
                    ).item()
                    ssim_scores.append(cos_sim)

                    result_entry["mse_vs_original"] = mse
                    result_entry["cosine_similarity"] = cos_sim

                    closest_idx = None
                    closest_dist = float("inf")
                    for j in range(min(100, len(class_indices))):
                        dist = nn.functional.mse_loss(
                            reconstructed, orig_samples[j:j+1]
                        ).item()
                        if dist < closest_dist:
                            closest_dist = dist
                            closest_idx = class_indices[j]
                    result_entry["closest_original_index"] = closest_idx
                    result_entry["closest_original_distance"] = closest_dist

            results.append(result_entry)

        attack_result = {
            "attack_name": "model-inversion-gradient",
            "num_target_classes": len(target_classes),
            "reconstructions": results,
            "avg_confidence": sum(confidence_scores) / max(len(confidence_scores), 1),
        }

        if mse_scores:
            attack_result["avg_mse_vs_original"] = sum(mse_scores) / len(mse_scores)
            attack_result["avg_cosine_similarity"] = sum(ssim_scores) / len(ssim_scores)

        overall_score = attack_result["avg_confidence"]
        attack_result["overall_score"] = overall_score
        if overall_score > 0.8:
            attack_result["risk_level"] = "high"
        elif overall_score > 0.5:
            attack_result["risk_level"] = "medium"
        else:
            attack_result["risk_level"] = "low"

        return attack_result
