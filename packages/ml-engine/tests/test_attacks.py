import pytest
import torch

from models.single_model import SingleModel
from security.attacks.model_extraction import ModelExtractionAttack
from security.attacks.model_inversion import ModelInversionAttack
from security.attacks.shadow_mia import ShadowModelMIA
from training.data import Dataset, generate_synthetic_data


@pytest.fixture
def trained_model():
    data = generate_synthetic_data(num_samples=200, num_features=10, seed=42)
    model = SingleModel(input_dim=10, num_classes=2)
    model.train(data.features, data.labels, epochs=50)
    return model, data


@pytest.mark.asyncio
class TestModelInversionAttack:
    async def test_reconstruct_returns_tensor(self, trained_model):
        model, data = trained_model
        attack = ModelInversionAttack(iterations=100, learning_rate=0.05)
        reconstructed = attack.reconstruct(model, target_class=0, input_dim=10)
        assert isinstance(reconstructed, torch.Tensor)
        assert reconstructed.shape == (1, 10)

    async def test_attack_returns_metrics(self, trained_model):
        model, data = trained_model
        attack = ModelInversionAttack(iterations=100, learning_rate=0.05)
        result = attack.attack(model, target_classes=[0, 1], original_dataset=data)
        assert result["attack_name"] == "model-inversion-gradient"
        assert result["num_target_classes"] == 2
        assert len(result["reconstructions"]) == 2
        for r in result["reconstructions"]:
            assert "target_class" in r
            assert "reconstructed_sample" in r
            assert "confidence" in r
        assert "avg_confidence" in result
        assert "avg_mse_vs_original" in result
        assert "risk_level" in result

    async def test_attack_without_original_data(self, trained_model):
        model, data = trained_model
        attack = ModelInversionAttack(iterations=50, learning_rate=0.05)
        result = attack.attack(model, target_classes=[0])
        assert result["num_target_classes"] == 1
        assert "avg_confidence" in result


@pytest.mark.asyncio
class TestShadowModelMIA:
    async def test_calibrate_trains_shadow_models(self, trained_model):
        model, data = trained_model
        attack = ShadowModelMIA(num_shadow_models=2, shadow_data_size=100, shadow_model_epochs=20)
        attack.calibrate(input_dim=10, num_classes=2)
        assert len(attack.shadow_models) == 2
        assert attack.attack_model is not None

    async def test_attack_returns_metrics(self, trained_model):
        model, data = trained_model
        split = data.size // 2
        target = data.get_subset(list(range(5)))
        member = data.get_subset(list(range(5, split)))
        nonmember = data.get_subset(list(range(split, data.size)))

        attack = ShadowModelMIA(num_shadow_models=2, shadow_data_size=100, shadow_model_epochs=20)
        result = attack.attack(model, target, member, nonmember)
        assert result["attack_name"] == "shadow-model-mia"
        assert result["num_shadow_models"] == 2
        assert "overall_accuracy" in result
        assert "precision" in result
        assert "recall" in result
        assert "f1_score" in result
        assert "member_accuracy" in result
        assert "nonmember_accuracy" in result


@pytest.mark.asyncio
class TestModelExtractionAttack:
    async def test_extract_returns_model(self, trained_model):
        model, data = trained_model
        attack = ModelExtractionAttack(extraction_epochs=50, num_queries=200)
        substitute = attack.extract(model, input_dim=10, num_classes=2)
        assert isinstance(substitute, SingleModel)
        assert attack.extracted_model is not None

    async def test_attack_returns_metrics(self, trained_model):
        model, data = trained_model
        attack = ModelExtractionAttack(extraction_epochs=50, num_queries=200)
        result = attack.attack(model, input_dim=10, num_classes=2, test_dataset=data)
        assert result["attack_name"] == "model-extraction"
        assert result["query_count"] == 200
        assert result["extraction_algorithm"] == "substitute-model"
        assert "functional_agreement" in result
        assert "confidence_similarity" in result
        assert "extraction_quality" in result
        assert "test_set_agreement" in result

    async def test_attack_with_query_budget(self, trained_model):
        model, data = trained_model
        attack = ModelExtractionAttack(extraction_epochs=30, num_queries=500)
        result = attack.attack(model, input_dim=10, num_classes=2, query_budget=100)
        assert result["query_count"] == 100
