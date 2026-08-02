import numpy as np
import pytest

from explainability.feature_attribution import FeatureAttribution
from explainability.integrated_gradients import IntegratedGradientsExplainer
from explainability.lime_explainer import LIMEExplainer
from explainability.shap_explainer import SHAPExplainer


def dummy_model(X):
    return np.mean(X, axis=1, keepdims=True)


class TestSHAPExplainer:
    def test_explain_returns_result(self):
        explainer = SHAPExplainer(dummy_model)
        inp = np.array([1.0, 0.5, 0.2, 0.8])
        result = explainer.explain(inp)
        assert result.method == "shap"
        assert len(result.feature_importances) == 4
        assert result.runtime_ms >= 0

    def test_explain_batch(self):
        explainer = SHAPExplainer(dummy_model)
        inputs = [np.array([1.0, 0.5]), np.array([0.8, 0.3])]
        results = explainer.explain_batch(inputs)
        assert len(results) == 2

    def test_global_feature_importance(self):
        explainer = SHAPExplainer(dummy_model)
        dataset = np.random.randn(10, 3)
        imp = explainer.global_feature_importance(dataset)
        assert len(imp) == 3

    def test_comparison_shap(self):
        explainer = SHAPExplainer(dummy_model)
        pre = np.random.randn(10, 3)
        post = np.random.randn(10, 3)
        comp = explainer.comparison_shap(pre, post)
        assert "pre_unlearning" in comp
        assert "importance_shift" in comp


class TestLIMEExplainer:
    def test_explain_returns_result(self):
        explainer = LIMEExplainer(dummy_model)
        inp = np.array([1.0, 0.5, 0.2])
        result = explainer.explain(inp)
        assert result.method == "lime"
        assert result.runtime_ms >= 0

    def test_explain_batch(self):
        explainer = LIMEExplainer(dummy_model)
        inputs = [np.array([1.0, 0.5]), np.array([0.8, 0.3])]
        results = explainer.explain_batch(inputs)
        assert len(results) == 2


class TestIntegratedGradientsExplainer:
    def test_explain_returns_result(self):
        explainer = IntegratedGradientsExplainer(dummy_model)
        inp = np.array([1.0, 0.5, 0.2])
        result = explainer.explain(inp)
        assert result.method == "integrated_gradients"
        assert result.ig_attributions is not None

    def test_feature_attribution_map(self):
        explainer = IntegratedGradientsExplainer(dummy_model)
        inp = np.array([1.0, 0.5, 0.2, 0.8])
        result = explainer.feature_attribution_map(inp)
        assert "attributions" in result


class TestFeatureAttribution:
    def test_gradient_attribution(self):
        explainer = FeatureAttribution(dummy_model, method="gradient")
        inp = np.array([1.0, 0.5, 0.2])
        result = explainer.explain(inp)
        assert "gradient" in result.method

    def test_occlusion_attribution(self):
        explainer = FeatureAttribution(dummy_model, method="occlusion")
        inp = np.array([1.0, 0.5, 0.2, 0.8])
        result = explainer.explain(inp)
        assert "occlusion" in result.method

    def test_aggregate_attributions(self):
        explainer = FeatureAttribution(dummy_model)
        results = [explainer.explain(np.array([1.0, 0.5, 0.2])) for _ in range(3)]
        agg = explainer.aggregate_attributions(results)
        assert len(agg) > 0
        assert "mean" in list(agg.values())[0]
