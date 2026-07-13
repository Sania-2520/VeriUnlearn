import logging
from typing import Optional

import torch
from torch import Tensor
import numpy as np

from models.single_model import SingleModel
from models.sharded_classifier import ShardedModel
from training.data import Dataset, generate_synthetic_data, generate_nonlinear_data

logger = logging.getLogger(__name__)


class ShadowModelMIA:
    def __init__(
        self,
        num_shadow_models: int = 5,
        shadow_model_epochs: int = 50,
        shadow_data_size: int = 200,
        device: Optional[torch.device] = None,
    ):
        self.num_shadow_models = num_shadow_models
        self.shadow_model_epochs = shadow_model_epochs
        self.shadow_data_size = shadow_data_size
        self.device = device or torch.device("cpu")
        self.shadow_models: list[SingleModel] = []
        self.attack_model: Optional[SingleModel] = None

    def _train_shadow_model(
        self,
        features: Tensor,
        labels: Tensor,
        input_dim: int,
        num_classes: int,
    ) -> SingleModel:
        shadow = SingleModel(
            input_dim=input_dim,
            num_classes=num_classes,
            device=self.device,
        )
        shadow.train(features, labels, epochs=self.shadow_model_epochs)
        return shadow

    def calibrate(
        self,
        input_dim: int,
        num_classes: int,
        seed: int = 42,
    ) -> None:
        self.shadow_models = []
        all_shadow_preds: list[Tensor] = []
        all_shadow_labels: list[int] = []

        rng = np.random.RandomState(seed)

        for i in range(self.num_shadow_models):
            model_seed = seed + i * 100
            shadow_data = generate_synthetic_data(
                num_samples=self.shadow_data_size,
                num_features=input_dim,
                num_classes=num_classes,
                seed=model_seed,
            )

            split = self.shadow_data_size // 2
            member_features = shadow_data.features[:split]
            member_labels = shadow_data.labels[:split]

            shadow_model = self._train_shadow_model(
                member_features, member_labels, input_dim, num_classes
            )
            self.shadow_models.append(shadow_model)

            with torch.no_grad():
                member_logits = shadow_model.predict_logits(member_features)
                member_probs = member_logits.softmax(dim=-1)
                member_max_conf = member_probs.max(dim=-1).values

            nonmember_features = shadow_data.features[split:]
            with torch.no_grad():
                nonmember_logits = shadow_model.predict_logits(nonmember_features)
                nonmember_probs = nonmember_logits.softmax(dim=-1)
                nonmember_max_conf = nonmember_probs.max(dim=-1).values

            all_shadow_preds.append(member_max_conf)
            all_shadow_preds.append(nonmember_max_conf)
            all_shadow_labels.extend([1] * len(member_max_conf))
            all_shadow_labels.extend([0] * len(nonmember_max_conf))

        if not all_shadow_preds:
            return

        all_preds = torch.cat(all_shadow_preds)
        attack_input = all_preds.unsqueeze(-1)
        attack_labels = torch.tensor(all_shadow_labels[:len(attack_input)], dtype=torch.long)

        self.attack_model = SingleModel(input_dim=1, num_classes=2, device=self.device)
        self.attack_model.train(attack_input, attack_labels, epochs=100)

    def attack(
        self,
        target_model: SingleModel | ShardedModel,
        target_dataset: Dataset,
        known_member_dataset: Dataset,
        known_nonmember_dataset: Dataset,
    ) -> dict:
        if not self.shadow_models or self.attack_model is None:
            input_dim = (
                target_model.input_dim
                if isinstance(target_model, SingleModel)
                else target_model.input_dim
            )
            num_classes = (
                target_model.num_classes
                if isinstance(target_model, SingleModel)
                else target_model.num_classes
            )
            self.calibrate(input_dim, num_classes)

        with torch.no_grad():
            target_logits = target_model.predict_logits(target_dataset.features)
            target_probs = target_logits.softmax(dim=-1)
            target_conf = target_probs.max(dim=-1).values.unsqueeze(-1)

            member_logits = target_model.predict_logits(known_member_dataset.features)
            member_probs = member_logits.softmax(dim=-1)
            member_conf = member_probs.max(dim=-1).values.unsqueeze(-1)

            nonmember_logits = target_model.predict_logits(known_nonmember_dataset.features)
            nonmember_probs = nonmember_logits.softmax(dim=-1)
            nonmember_conf = nonmember_probs.max(dim=-1).values.unsqueeze(-1)

        member_preds = self.attack_model.predict(member_conf)
        nonmember_preds = self.attack_model.predict(nonmember_conf)
        target_preds = self.attack_model.predict(target_conf)

        member_members = (member_preds == 1).float()
        nonmember_nonmembers = (nonmember_preds == 0).float()
        target_members = (target_preds == 1).float()

        member_acc = member_members.mean().item()
        nonmember_acc = nonmember_nonmembers.mean().item()
        overall_acc = (
            (member_members.sum() + nonmember_nonmembers.sum()).item()
            / max(len(member_members) + len(nonmember_nonmembers), 1)
        )

        tp = member_members.sum().item()
        fp = len(nonmember_nonmembers) - nonmember_nonmembers.sum().item()
        fn = len(member_members) - tp
        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-8)

        return {
            "attack_name": "shadow-model-mia",
            "num_shadow_models": self.num_shadow_models,
            "attack_model_type": "mlp",
            "member_accuracy": member_acc,
            "nonmember_accuracy": nonmember_acc,
            "overall_accuracy": overall_acc,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "target_members_found": int(target_members.sum().item()),
            "target_total": len(target_preds),
        }
