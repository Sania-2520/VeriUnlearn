import math
from typing import Any, Optional

import torch

from models.single_model import SingleModel
from models.sharded_classifier import ShardedModel
from security.attacks.membership_inference import LossBasedMIA, MembershipInferenceAttack
from training.data import Dataset


class PrivacyEvaluationReport:
    def __init__(
        self,
        mia_risk: dict,
        loss_mia_risk: dict,
        epsilon_estimate: Optional[float],
        delta_estimate: Optional[float],
        reid_risk: float,
        attribute_disclosure_risk: float,
        overall_score: float,
    ):
        self.mia_risk = mia_risk
        self.loss_mia_risk = loss_mia_risk
        self.epsilon_estimate = epsilon_estimate
        self.delta_estimate = delta_estimate
        self.reid_risk = reid_risk
        self.attribute_disclosure_risk = attribute_disclosure_risk
        self.overall_score = overall_score

    def to_dict(self) -> dict:
        return {
            "membership_inference": {
                "confidence_based": {
                    "overall_accuracy": self.mia_risk.get("overall_accuracy", 0),
                    "f1_score": self.mia_risk.get("f1_score", 0),
                },
                "loss_based": {
                    "overall_accuracy": self.loss_mia_risk.get("overall_accuracy", 0),
                    "f1_score": self.loss_mia_risk.get("f1_score", 0),
                },
            },
            "dp_estimate": {
                "epsilon": self.epsilon_estimate,
                "delta": self.delta_estimate,
            },
            "reidentification_risk": self.reid_risk,
            "attribute_disclosure_risk": self.attribute_disclosure_risk,
            "overall_privacy_score": self.overall_score,
            "risk_level": self._risk_level(),
        }

    def _risk_level(self) -> str:
        if self.overall_score < 0.3:
            return "low"
        if self.overall_score < 0.6:
            return "medium"
        return "high"


class PrivacyEvaluator:
    def evaluate(
        self,
        model: SingleModel | ShardedModel,
        original_dataset: Dataset,
        retained_dataset: Dataset,
        unlearned_ids: set[str],
        epsilon: Optional[float] = None,
        delta: Optional[float] = None,
    ) -> PrivacyEvaluationReport:
        confidence_mia = MembershipInferenceAttack(threshold_percentile=5.0)
        loss_mia = LossBasedMIA(threshold_percentile=10.0)

        unlearned_data = original_dataset.get_by_ids(unlearned_ids)
        held_out = retained_dataset.get_subset(
            list(range(min(50, retained_dataset.size)))
        )
        member_data = retained_dataset.get_subset(
            list(range(50, min(100, retained_dataset.size)))
        )

        num_classes = original_dataset.labels.unique().size(0)
        member_dataset = member_data
        nonmember_dataset = held_out
        target_dataset = unlearned_data

        if target_dataset.size == 0:
            target_dataset = held_out

        if member_dataset.size == 0 or nonmember_dataset.size == 0:
            split = retained_dataset.size // 2
            member_dataset = retained_dataset.get_subset(list(range(split)))
            nonmember_dataset = retained_dataset.get_subset(
                list(range(split, min(split * 2, retained_dataset.size)))
            )

        conf_result = confidence_mia.attack(
            model,
            target_dataset.features,
            member_dataset.features,
            nonmember_dataset.features,
        )

        loss_result = loss_mia.attack(
            model,
            target_dataset,
            member_dataset,
            nonmember_dataset,
        )

        mia_overall = max(
            conf_result.get("overall_accuracy", 0),
            loss_result.get("overall_accuracy", 0),
        )

        privacy_score = mia_overall
        if epsilon is not None and epsilon > 0:
            dp_privacy = 1.0 / (1.0 + epsilon)
            privacy_score = privacy_score * 0.4 + (1.0 - dp_privacy) * 0.6

        reid_risk = max(
            0.0,
            min(
                1.0,
                conf_result.get("precision", 0),
            ),
        )

        attr_risk = max(
            0.0,
            min(1.0, loss_result.get("recall", 0)),
        )

        return PrivacyEvaluationReport(
            mia_risk=conf_result,
            loss_mia_risk=loss_result,
            epsilon_estimate=epsilon,
            delta_estimate=delta,
            reid_risk=reid_risk,
            attribute_disclosure_risk=attr_risk,
            overall_score=privacy_score,
        )
