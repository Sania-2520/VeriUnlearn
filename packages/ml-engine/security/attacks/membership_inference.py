import math
from typing import Optional

import torch
from torch import Tensor

from models.sharded_classifier import ShardedModel
from models.single_model import SingleModel
from training.data import Dataset


class MembershipInferenceAttack:
    def __init__(self, threshold_percentile: float = 5.0):
        self.threshold_percentile = threshold_percentile
        self.threshold: Optional[float] = None

    def calibrate(
        self,
        model: SingleModel | ShardedModel,
        holdout_data: Dataset,
    ) -> float:
        if isinstance(model, SingleModel):
            logits = model.predict_logits(holdout_data.features)
        else:
            logits = model.predict_logits(holdout_data.features)
        probs = logits.softmax(dim=-1)
        confidence = probs.max(dim=-1).values
        sorted_conf = confidence.sort().values
        idx = max(0, int(len(sorted_conf) * self.threshold_percentile / 100.0) - 1)
        self.threshold = sorted_conf[idx].item()
        return self.threshold

    def predict(self, features: Tensor, model: SingleModel | ShardedModel) -> list[dict]:
        if isinstance(model, SingleModel):
            logits = model.predict_logits(features)
        else:
            logits = model.predict_logits(features)
        probs = logits.softmax(dim=-1)
        confidence = probs.max(dim=-1).values

        threshold = self.threshold
        if threshold is None:
            threshold = confidence.mean().item()

        results = []
        for i in range(len(features)):
            is_member = confidence[i].item() >= threshold
            results.append({
                "index": i,
                "confidence": confidence[i].item(),
                "predicted_member": is_member,
                "threshold": threshold,
            })
        return results

    def attack(
        self,
        model: SingleModel | ShardedModel,
        target_features: Tensor,
        known_member_features: Tensor,
        known_nonmember_features: Tensor,
    ) -> dict:
        self.calibrate(model, Dataset(
            features=known_nonmember_features,
            labels=torch.zeros(len(known_nonmember_features), dtype=torch.long),
        ))

        member_preds = self.predict(known_member_features, model)
        member_correct = sum(1 for p in member_preds if p["predicted_member"])
        member_rate = member_correct / max(len(member_preds), 1)

        nonmember_preds = self.predict(known_nonmember_features, model)
        nonmember_incorrect = sum(1 for p in nonmember_preds if not p["predicted_member"])
        nonmember_rate = nonmember_incorrect / max(len(nonmember_preds), 1)

        target_preds = self.predict(target_features, model)
        target_members = sum(1 for p in target_preds if p["predicted_member"])

        accuracy = (member_correct + nonmember_incorrect) / max(
            len(member_preds) + len(nonmember_preds), 1
        )

        return {
            "attack_name": "confidence-threshold",
            "threshold": self.threshold,
            "member_accuracy": member_rate,
            "nonmember_accuracy": nonmember_rate,
            "overall_accuracy": accuracy,
            "precision": (
                member_correct / max(member_correct + (len(nonmember_preds) - nonmember_incorrect), 1)
            ),
            "recall": member_correct / max(len(member_preds), 1),
            "f1_score": (
                2 * member_correct
                / max(
                    2 * member_correct
                    + (len(nonmember_preds) - nonmember_incorrect)
                    + (len(member_preds) - member_correct),
                    1,
                )
            ),
            "target_members_found": target_members,
            "target_total": len(target_preds),
        }


class LossBasedMIA:
    def __init__(self, threshold_percentile: float = 10.0):
        self.threshold_percentile = threshold_percentile
        self.threshold: Optional[float] = None

    def calibrate(
        self,
        model: SingleModel | ShardedModel,
        holdout_data: Dataset,
    ) -> float:
        features, labels = holdout_data.features, holdout_data.labels
        if isinstance(model, SingleModel):
            logits = model.predict_logits(features)
        else:
            logits = model.predict_logits(features)
        loss = torch.nn.functional.cross_entropy(logits, labels, reduction="none")
        sorted_loss = loss.sort().values
        idx = min(
            len(sorted_loss) - 1,
            int(len(sorted_loss) * (100 - self.threshold_percentile) / 100.0),
        )
        self.threshold = sorted_loss[idx].item()
        return self.threshold

    def attack(
        self,
        model: SingleModel | ShardedModel,
        target_dataset: Dataset,
        member_dataset: Dataset,
        nonmember_dataset: Dataset,
    ) -> dict:
        self.calibrate(model, nonmember_dataset)

        features, labels = target_dataset.features, target_dataset.labels
        if isinstance(model, SingleModel):
            logits = model.predict_logits(features)
        else:
            logits = model.predict_logits(features)
        target_losses = torch.nn.functional.cross_entropy(logits, labels, reduction="none")

        member_features, member_labels = member_dataset.features, member_dataset.labels
        if isinstance(model, SingleModel):
            member_logits = model.predict_logits(member_features)
        else:
            member_logits = model.predict_logits(member_features)
        member_losses = torch.nn.functional.cross_entropy(
            member_logits, member_labels, reduction="none"
        )

        nonmember_features, nonmember_labels = nonmember_dataset.features, nonmember_dataset.labels
        if isinstance(model, SingleModel):
            non_logits = model.predict_logits(nonmember_features)
        else:
            non_logits = model.predict_logits(nonmember_features)
        nonmember_losses = torch.nn.functional.cross_entropy(
            non_logits, nonmember_labels, reduction="none"
        )

        threshold = self.threshold
        member_preds = (member_losses < threshold).float()
        nonmember_preds = (nonmember_losses >= threshold).float()
        target_preds = (target_losses < threshold).float()

        member_acc = member_preds.mean().item()
        nonmember_acc = nonmember_preds.mean().item()
        overall_acc = (member_preds.sum() + nonmember_preds.sum()).item() / max(
            len(member_preds) + len(nonmember_preds), 1
        )

        tp = member_preds.sum().item()
        fp = len(nonmember_preds) - nonmember_preds.sum().item()
        fn = len(member_preds) - tp
        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-8)

        return {
            "attack_name": "loss-threshold",
            "threshold": threshold,
            "member_accuracy": member_acc,
            "nonmember_accuracy": nonmember_acc,
            "overall_accuracy": overall_acc,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "target_members_found": int(target_preds.sum().item()),
            "target_total": len(target_preds),
        }
