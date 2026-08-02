import pytest
import torch

from models.single_model import SingleModel
from security.attacks.membership_inference import LossBasedMIA, MembershipInferenceAttack
from training.data import generate_synthetic_data
from verification.privacy_evaluation import PrivacyEvaluator


@pytest.fixture
def trained_model():
    data = generate_synthetic_data(num_samples=200, num_features=10, seed=42)
    model = SingleModel(input_dim=10, num_classes=2)
    model.train(data.features, data.labels, epochs=50)
    return model, data


@pytest.mark.asyncio
class TestMembershipInferenceAttack:
    async def test_calibrate_sets_threshold(self, trained_model):
        model, data = trained_model
        holdout = data.get_subset(list(range(100)))
        mia = MembershipInferenceAttack(threshold_percentile=5.0)
        threshold = mia.calibrate(model, holdout)
        assert threshold > 0
        assert mia.threshold == threshold

    async def test_predict_returns_results(self, trained_model):
        model, data = trained_model
        mia = MembershipInferenceAttack()
        results = mia.predict(data.features[:10], model)
        assert len(results) == 10
        for r in results:
            assert "confidence" in r
            assert "predicted_member" in r
            assert "threshold" in r

    async def test_attack_returns_metrics(self, trained_model):
        model, data = trained_model
        split = data.size // 2
        target = data.get_subset(list(range(5)))
        member = data.get_subset(list(range(5, split)))
        nonmember = data.get_subset(list(range(split, data.size)))
        mia = MembershipInferenceAttack()
        result = mia.attack(model, target.features, member.features, nonmember.features)
        assert "overall_accuracy" in result
        assert "precision" in result
        assert "recall" in result
        assert "f1_score" in result
        assert result["target_total"] == 5


@pytest.mark.asyncio
class TestLossBasedMIA:
    async def test_calibrate_sets_threshold(self, trained_model):
        model, data = trained_model
        holdout = data.get_subset(list(range(50)))
        mia = LossBasedMIA(threshold_percentile=10.0)
        threshold = mia.calibrate(model, holdout)
        assert threshold > 0

    async def test_attack_returns_metrics(self, trained_model):
        model, data = trained_model
        split = data.size // 2
        target = data.get_subset(list(range(5)))
        member = data.get_subset(list(range(5, split)))
        nonmember = data.get_subset(list(range(split, data.size)))
        mia = LossBasedMIA()
        result = mia.attack(model, target, member, nonmember)
        assert "overall_accuracy" in result
        assert "f1_score" in result
        assert result["target_total"] == 5


@pytest.mark.asyncio
class TestPrivacyEvaluator:
    async def test_evaluate_returns_report(self, trained_model):
        model, data = trained_model
        unlearned_ids = {"data_000000", "data_000001"}
        retained = data.remove_by_ids(unlearned_ids)
        evaluator = PrivacyEvaluator()
        report = evaluator.evaluate(
            model=model,
            original_dataset=data,
            retained_dataset=retained,
            unlearned_ids=unlearned_ids,
            epsilon=0.5,
            delta=1e-5,
        )
        d = report.to_dict()
        assert "membership_inference" in d
        assert "dp_estimate" in d
        assert "overall_privacy_score" in d
        assert "risk_level" in d
        assert d["dp_estimate"]["epsilon"] == 0.5
        assert d["risk_level"] in ("low", "medium", "high")

    async def test_evaluate_with_inversion_and_extraction(self, trained_model):
        model, data = trained_model
        unlearned_ids = {"data_000000", "data_000001"}
        retained = data.remove_by_ids(unlearned_ids)
        evaluator = PrivacyEvaluator()
        report = evaluator.evaluate(
            model=model,
            original_dataset=data,
            retained_dataset=retained,
            unlearned_ids=unlearned_ids,
            run_inversion=True,
            run_extraction=True,
        )
        d = report.to_dict()
        assert "model_inversion" in d
        assert "model_extraction" in d
        assert d["model_inversion"]["attack_name"] == "model-inversion-gradient"
        assert d["model_extraction"]["attack_name"] == "model-extraction"

    async def test_evaluate_without_epsilon(self, trained_model):
        model, data = trained_model
        retained = data.remove_by_ids({"data_000000"})
        evaluator = PrivacyEvaluator()
        report = evaluator.evaluate(
            model=model,
            original_dataset=data,
            retained_dataset=retained,
            unlearned_ids={"data_000000"},
        )
        d = report.to_dict()
        assert d["dp_estimate"]["epsilon"] is None

    async def test_report_to_dict_structure(self):
        from verification.privacy_evaluation import PrivacyEvaluationReport
        report = PrivacyEvaluationReport(
            mia_risk={"overall_accuracy": 0.7, "f1_score": 0.65},
            loss_mia_risk={"overall_accuracy": 0.6, "f1_score": 0.55},
            epsilon_estimate=1.0,
            delta_estimate=1e-5,
            reid_risk=0.3,
            attribute_disclosure_risk=0.2,
            overall_score=0.4,
        )
        d = report.to_dict()
        assert d["membership_inference"]["confidence_based"]["overall_accuracy"] == 0.7
        assert d["dp_estimate"]["epsilon"] == 1.0
        assert d["risk_level"] == "medium"
