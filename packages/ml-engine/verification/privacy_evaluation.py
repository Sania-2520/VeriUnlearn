import math
from typing import Any, Optional

import torch

from models.single_model import SingleModel
from models.sharded_classifier import ShardedModel
from security.attacks.membership_inference import LossBasedMIA, MembershipInferenceAttack
from security.attacks.model_inversion import ModelInversionAttack
from security.attacks.model_extraction import ModelExtractionAttack
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
        inversion_risk: Optional[dict] = None,
        extraction_risk: Optional[dict] = None,
    ):
        self.mia_risk = mia_risk
        self.loss_mia_risk = loss_mia_risk
        self.epsilon_estimate = epsilon_estimate
        self.delta_estimate = delta_estimate
        self.reid_risk = reid_risk
        self.attribute_disclosure_risk = attribute_disclosure_risk
        self.overall_score = overall_score
        self.inversion_risk = inversion_risk
        self.extraction_risk = extraction_risk

    def to_dict(self) -> dict:
        result = {
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
        if self.inversion_risk is not None:
            result["model_inversion"] = self.inversion_risk
        if self.extraction_risk is not None:
            result["model_extraction"] = self.extraction_risk
        return result

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
        run_inversion: bool = False,
        run_extraction: bool = False,
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

        inversion_risk: Optional[dict] = None
        extraction_risk: Optional[dict] = None

        if run_inversion:
            try:
                num_classes = len(original_dataset.labels.unique())
                inv_attack = ModelInversionAttack(iterations=200)
                target_classes = list(range(min(num_classes, 3)))
                inv_result = inv_attack.attack(
                    model, target_classes, original_dataset=original_dataset
                )
                inversion_risk = inv_result
            except Exception:
                inversion_risk = {"error": "model inversion attack failed"}

        if run_extraction:
            try:
                input_dim = (
                    model.input_dim
                    if isinstance(model, SingleModel)
                    else model.input_dim
                )
                num_classes = (
                    model.num_classes
                    if isinstance(model, SingleModel)
                    else model.num_classes
                )
                ext_attack = ModelExtractionAttack(extraction_epochs=100)
                ext_result = ext_attack.attack(
                    model, input_dim, num_classes, test_dataset=original_dataset
                )
                extraction_risk = ext_result
            except Exception:
                extraction_risk = {"error": "model extraction attack failed"}

        return PrivacyEvaluationReport(
            mia_risk=conf_result,
            loss_mia_risk=loss_result,
            epsilon_estimate=epsilon,
            delta_estimate=delta,
            reid_risk=reid_risk,
            attribute_disclosure_risk=attr_risk,
            overall_score=privacy_score,
            inversion_risk=inversion_risk,
            extraction_risk=extraction_risk,
        )
