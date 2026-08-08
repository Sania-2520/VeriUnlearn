"""Explainability endpoints (SHAP, LIME, gradients, counterfactuals, embedding)."""

import numpy as np
from fastapi import APIRouter

from api import deps
from api.schemas import (
    DriftRequest,
    ExplainCompareRequest,
    ExplainFeaturesRequest,
    ExplainSamplesRequest,
    PrivacyHeatmapRequest,
)

router = APIRouter()


@router.post("/explain/samples")
async def explain_samples(request: ExplainSamplesRequest):
    from explainability.visualization import ExplanationVisualizer

    mgr = deps.get_explainer_manager()
    samples_np = [np.array(s, dtype=np.float32) for s in request.samples]
    method = request.method.lower()

    if method == "shap":
        explainer = mgr.get_shap()
    elif method == "lime":
        explainer = mgr.get_lime()
    elif method in ("integrated_gradients", "ig"):
        explainer = mgr.get_ig()
    elif method in ("gradient", "occlusion", "perturbation"):
        explainer = mgr.get_attr(method=method)
    else:
        explainer = mgr.get_shap()

    results = explainer.explain_batch(samples_np)
    chart_data = [ExplanationVisualizer.importance_chart_data(r) for r in results]
    return {
        "method": method,
        "count": len(results),
        "results": [
            {
                "feature_importances": [
                    {"feature": fi.feature_name, "importance": fi.importance_score, "direction": fi.direction}
                    for fi in r.feature_importances
                ],
                "prediction": r.prediction,
                "confidence": r.confidence,
                "runtime_ms": r.runtime_ms,
            }
            for r in results
        ],
        "chart_data": chart_data,
    }


@router.post("/explain/features")
async def explain_features(request: ExplainFeaturesRequest):
    mgr = deps.get_explainer_manager()
    dataset_np = np.array(request.dataset, dtype=np.float32)
    method = request.method.lower()

    if method == "shap":
        explainer = mgr.get_shap()
        global_importance = explainer.global_feature_importance(dataset_np)
    else:
        explainer = mgr.get_attr(method=method if method in ("gradient", "occlusion", "perturbation") else "gradient")
        results = explainer.explain_batch([row for row in dataset_np])
        agg = explainer.aggregate_attributions(results)
        global_importance = {k: v["mean"] for k, v in agg.items()}

    return {
        "method": method,
        "samples": len(request.dataset),
        "features": len(request.feature_names or global_importance),
        "feature_names": request.feature_names or list(global_importance.keys()),
        "global_importance": global_importance,
    }


@router.post("/explain/compare")
async def compare_explanations(request: ExplainCompareRequest):
    from explainability.visualization import ExplanationVisualizer

    mgr = deps.get_explainer_manager()
    pre_samples = [np.array(s, dtype=np.float32) for s in request.pre_unlearn_samples]
    post_samples = [np.array(s, dtype=np.float32) for s in request.post_unlearn_samples]
    method = request.method.lower()

    if method == "shap":
        explainer = mgr.get_shap()
    elif method == "lime":
        explainer = mgr.get_lime()
    elif method in ("integrated_gradients", "ig"):
        explainer = mgr.get_ig()
    elif method in ("gradient", "occlusion", "perturbation"):
        explainer = mgr.get_attr(method=method)
    else:
        explainer = mgr.get_shap()

    pre_results = explainer.explain_batch(pre_samples)
    post_results = explainer.explain_batch(post_samples)

    comparisons = []
    for pre, post in zip(pre_results, post_results):
        comparisons.append(ExplanationVisualizer.comparison_chart_data(pre, post))

    return {
        "method": method,
        "pair_count": min(len(pre_results), len(post_results)),
        "comparisons": comparisons,
    }


@router.post("/explain/privacy-heatmap")
async def privacy_heatmap(request: PrivacyHeatmapRequest):
    from explainability.visualization import ExplanationVisualizer

    mgr = deps.get_explainer_manager()
    samples_np = [np.array(s, dtype=np.float32) for s in request.samples]
    explainer = mgr.get_shap()
    results = explainer.explain_batch(samples_np)

    importances = []
    for r in results:
        row = {}
        for fi in r.feature_importances:
            row[fi.feature_name] = fi.importance_score
        importances.append(row)

    heatmap = ExplanationVisualizer.privacy_risk_heatmap(
        importances, request.privacy_scores, request.feature_names
    )
    return heatmap


@router.post("/explain/drift")
async def model_drift(request: DriftRequest):
    from explainability.visualization import ExplanationVisualizer

    summary = ExplanationVisualizer.drift_summary(
        request.pre_confidences,
        request.post_confidences,
        request.pre_importances,
        request.post_importances,
    )
    return summary


@router.get("/explain/methods")
async def list_explain_methods():
    return {
        "methods": [
            {"id": "shap", "name": "SHAP", "description": "SHAP (SHapley Additive exPlanations) — game-theoretic feature importance"},
            {"id": "lime", "name": "LIME", "description": "Local Interpretable Model-agnostic Explanations — local surrogate models"},
            {"id": "integrated_gradients", "name": "Integrated Gradients", "description": "Attribution via path integral of gradients"},
            {"id": "gradient", "name": "Gradient Attribution", "description": "Simple gradient-based feature attribution"},
            {"id": "occlusion", "name": "Occlusion", "description": "Feature occlusion / ablation-based attribution"},
            {"id": "perturbation", "name": "Perturbation", "description": "Random perturbation-based feature importance"},
            {"id": "counterfactual", "name": "Counterfactual Explanations", "description": "Minimum perturbation to flip model prediction"},
            {"id": "embedding_pca", "name": "Embedding PCA", "description": "PCA dimensionality reduction for embedding visualization"},
            {"id": "embedding_umap", "name": "Embedding UMAP", "description": "UMAP dimensionality reduction for embedding visualization"},
        ]
    }


@router.post("/explain/counterfactual")
async def explain_counterfactual(request: dict):
    import torch

    samples = request.get("samples", [])
    target_class = request.get("target_class", 0)
    num_steps = request.get("num_steps", 500)
    mgr = deps.get_explainer_manager()
    cf = deps.get_counterfactual()

    shap_explainer = mgr.get_shap()
    sample_arrays = [np.array(s, dtype=np.float32) for s in samples]

    class WrapperModel:
        def __init__(self, explainer):
            self.explainer = explainer

        def __call__(self, x):
            results = self.explainer.explain_batch([x_i.numpy() for x_i in x])
            return torch.tensor([[r.confidence, 1 - r.confidence] for r in results])

        def eval(self):
            return self

        def parameters(self):
            return []

        def to(self, device):
            return self

    wrapper = WrapperModel(shap_explainer)
    cf.set_model(wrapper)

    results = []
    for s in sample_arrays:
        result = cf.generate(s, target_class, num_steps=num_steps)
        results.append(result)

    return {"method": "counterfactual", "target_class": target_class, "count": len(results), "results": results}


@router.post("/explain/embedding-viz")
async def embedding_visualization(request: dict):
    viz = deps.get_embedding_viz()
    embeddings = np.array(request.get("embeddings", []), dtype=np.float32)
    labels = request.get("labels")
    method = request.get("method", "pca")
    viz.method = method
    result = viz.reduce(embeddings, labels=labels)
    return result


@router.post("/explain/embedding-compare")
async def embedding_compare(request: dict):
    viz = deps.get_embedding_viz()
    pre = np.array(request.get("pre_embeddings", []), dtype=np.float32)
    post = np.array(request.get("post_embeddings", []), dtype=np.float32)
    labels = request.get("labels")
    return viz.compare(pre, post, labels=labels)


@router.post("/explain/privacy-shift")
async def privacy_shift_analysis(request: dict):
    viz = deps.get_embedding_viz()
    before = np.array(request.get("before_unlearn", []), dtype=np.float32)
    after = np.array(request.get("after_unlearn", []), dtype=np.float32)
    return viz.privacy_shift(before, after)
