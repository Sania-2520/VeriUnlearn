import logging
from typing import Optional

import torch
from torch import Tensor, nn
from torch.optim import Adam

from models.single_model import SingleModel
from models.sharded_classifier import ShardedModel
from training.data import Dataset

logger = logging.getLogger(__name__)


class ModelExtractionAttack:
    def __init__(
        self,
        learning_rate: float = 1e-2,
        extraction_epochs: int = 200,
        num_queries: int = 1000,
        device: Optional[torch.device] = None,
    ):
        self.learning_rate = learning_rate
        self.extraction_epochs = extraction_epochs
        self.num_queries = num_queries
        self.device = device or torch.device("cpu")
        self.extracted_model: Optional[SingleModel] = None

    def extract(
        self,
        victim_model: SingleModel | ShardedModel,
        input_dim: int,
        num_classes: int,
        synthetic_data: Optional[Tensor] = None,
    ) -> SingleModel:
        substitute = SingleModel(
            input_dim=input_dim,
            num_classes=num_classes,
            learning_rate=self.learning_rate,
            device=self.device,
        )

        if synthetic_data is not None:
            queries = synthetic_data.to(self.device)
        else:
            queries = torch.randn(self.num_queries, input_dim, device=self.device)

        with torch.no_grad():
            if isinstance(victim_model, SingleModel):
                victim_logits = victim_model.predict_logits(queries)
            else:
                victim_logits = victim_model.predict_logits(queries)

        substitute.train(queries, victim_logits.argmax(dim=-1), epochs=self.extraction_epochs)

        self.extracted_model = substitute

        sub_preds = substitute.predict(queries)
        victim_labels = victim_logits.argmax(dim=-1)
        agreement = (sub_preds == victim_labels).float().mean().item()

        return substitute

    def attack(
        self,
        victim_model: SingleModel | ShardedModel,
        input_dim: int,
        num_classes: int,
        test_dataset: Optional[Dataset] = None,
        query_budget: Optional[int] = None,
    ) -> dict:
        actual_queries = query_budget if query_budget is not None else self.num_queries
        queries = torch.randn(actual_queries, input_dim, device=self.device)

        self.extract(victim_model, input_dim, num_classes, synthetic_data=queries)

        if self.extracted_model is None:
            return {"attack_name": "model-extraction", "error": "extraction failed"}

        test_queries = torch.randn(min(500, actual_queries), input_dim, device=self.device)
        with torch.no_grad():
            if isinstance(victim_model, SingleModel):
                victim_logits = victim_model.predict_logits(test_queries)
            else:
                victim_logits = victim_model.predict_logits(test_queries)
        victim_labels = victim_logits.argmax(dim=-1)

        sub_preds = self.extracted_model.predict(test_queries)
        agreement = (sub_preds == victim_labels).float().mean().item()

        victim_probs = victim_logits.softmax(dim=-1)
        victim_conf = victim_probs.max(dim=-1).values

        sub_logits = self.extracted_model.predict_logits(test_queries)
        sub_probs = sub_logits.softmax(dim=-1)
        sub_conf = sub_probs.max(dim=-1).values

        confidence_similarity = nn.functional.cosine_similarity(
            victim_conf.unsqueeze(0), sub_conf.unsqueeze(0)
        ).item()

        result = {
            "attack_name": "model-extraction",
            "extraction_algorithm": "substitute-model",
            "query_count": actual_queries,
            "substitute_architecture": "SimpleNet",
            "functional_agreement": agreement,
            "confidence_similarity": confidence_similarity,
            "extraction_quality": "high" if agreement > 0.8 else "medium" if agreement > 0.5 else "low",
        }

        if test_dataset is not None:
            with torch.no_grad():
                if isinstance(victim_model, SingleModel):
                    test_victim_logits = victim_model.predict_logits(test_dataset.features)
                else:
                    test_victim_logits = victim_model.predict_logits(test_dataset.features)
            test_victim_labels = test_victim_logits.argmax(dim=-1)
            test_sub_preds = self.extracted_model.predict(test_dataset.features)
            test_agreement = (test_sub_preds == test_victim_labels).float().mean().item()
            result["test_set_agreement"] = test_agreement

        return result
