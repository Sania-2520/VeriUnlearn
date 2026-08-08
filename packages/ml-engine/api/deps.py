"""Dependency providers and shared singletons for the ML Engine API.

Centralising lazy singletons here (instead of in the historical ``api.py``
monolith) lets every router depend on the same instances and lets the health
endpoints inspect what is currently loaded without importing framework code.
"""

from typing import Any, Optional

import numpy as np

from unlearning.hybrid_controller import HybridAdaptiveController
from verification.privacy_evaluation import PrivacyEvaluator
from verification.signatures import SignatureManager

# Shared, eagerly-created singletons (cheap, framework-independent).
controller = HybridAdaptiveController()
sig_manager = SignatureManager()
privacy_evaluator = PrivacyEvaluator()

# Lazy-initialized metainfo singletons for heavier components. Each is created
# once on first use to keep process startup fast.
_lora_trainer: Optional[Any] = None
_model_registry: Optional[Any] = None
_rag_pipeline: Optional[Any] = None
_inference_service: Optional[Any] = None
_conversational_pipeline: Optional[Any] = None
_mlflow_tracker: Optional[Any] = None
_e2e_pipeline: Optional[Any] = None
_explainer_manager: Optional[Any] = None
_adapter_lifecycle: Optional[Any] = None
_continual_learning: Optional[Any] = None
_benchmark_runner: Optional[Any] = None
_distiller: Optional[Any] = None
_gpu_scheduler: Optional[Any] = None
_counterfactual: Optional[Any] = None
_embedding_viz: Optional[Any] = None


def get_lora_trainer():
    global _lora_trainer
    if _lora_trainer is None:
        from training.lora_trainer import LoRATrainer, TrainingConfig

        _lora_trainer = LoRATrainer(TrainingConfig())
    return _lora_trainer


def get_model_registry():
    global _model_registry
    if _model_registry is None:
        from training.model_registry import ModelRegistry, RegistryConfig

        _model_registry = ModelRegistry(RegistryConfig())
    return _model_registry


def get_rag_pipeline():
    global _rag_pipeline
    if _rag_pipeline is None:
        from training.rag_pipeline import RAGConfig, RAGPipeline

        _rag_pipeline = RAGPipeline(RAGConfig())
    return _rag_pipeline


def get_inference_service():
    global _inference_service
    if _inference_service is None:
        from inference.service import InferenceConfig, InferenceService

        _inference_service = InferenceService(InferenceConfig())
    return _inference_service


def get_conversational_pipeline():
    global _conversational_pipeline
    if _conversational_pipeline is None:
        from training.conversational_pipeline import (
            ConversationalLearningPipeline,
            PipelineConfig,
        )

        _conversational_pipeline = ConversationalLearningPipeline(PipelineConfig())
    return _conversational_pipeline


def get_continual_learning():
    global _continual_learning
    if _continual_learning is None:
        from training.continual_learning import ContinualLearningManager

        _continual_learning = ContinualLearningManager()
    return _continual_learning


def get_benchmark_runner():
    global _benchmark_runner
    if _benchmark_runner is None:
        from training.benchmarks import BenchmarkConfig, BenchmarkRunner

        _benchmark_runner = BenchmarkRunner(BenchmarkConfig())
    return _benchmark_runner


def get_mlflow_tracker():
    global _mlflow_tracker
    if _mlflow_tracker is None:
        from training.mlflow_tracker import MLflowConfig, MLflowExperimentTracker

        _mlflow_tracker = MLflowExperimentTracker(MLflowConfig())
    return _mlflow_tracker


def get_e2e_pipeline():
    global _e2e_pipeline
    if _e2e_pipeline is None:
        from unlearning.e2e_pipeline import E2EUnlearningPipeline

        _e2e_pipeline = E2EUnlearningPipeline()
    return _e2e_pipeline


class ExplainerManager:
    """Lazy holder for SHAP / LIME / Integrated-Gradients / attribution engines."""

    def __init__(self) -> None:
        self._shap: Optional[Any] = None
        self._lime: Optional[Any] = None
        self._ig: Optional[Any] = None
        self._attr: Optional[Any] = None

    @staticmethod
    def _dummy_model():
        def model_fn(X):
            return np.mean(X, axis=1, keepdims=True)

        return model_fn

    def get_shap(self, model=None) -> Any:
        if self._shap is None:
            from explainability.shap_explainer import SHAPExplainer

            self._shap = SHAPExplainer(model or self._dummy_model())
        return self._shap

    def get_lime(self, model=None) -> Any:
        if self._lime is None:
            from explainability.lime_explainer import LIMEExplainer

            self._lime = LIMEExplainer(model or self._dummy_model())
        return self._lime

    def get_ig(self, model=None) -> Any:
        if self._ig is None:
            from explainability.integrated_gradients import IntegratedGradientsExplainer

            self._ig = IntegratedGradientsExplainer(model or self._dummy_model())
        return self._ig

    def get_attr(self, model=None, method="gradient") -> Any:
        if self._attr is None or self._attr._method != method:
            from explainability.feature_attribution import FeatureAttribution

            self._attr = FeatureAttribution(model or self._dummy_model(), method=method)
        return self._attr


def get_explainer_manager():
    global _explainer_manager
    if _explainer_manager is None:
        _explainer_manager = ExplainerManager()
    return _explainer_manager


def get_adapter_lifecycle():
    global _adapter_lifecycle
    if _adapter_lifecycle is None:
        from training.adapter_lifecycle import AdapterLifecycleManager, LifecycleConfig

        _adapter_lifecycle = AdapterLifecycleManager(LifecycleConfig())
    return _adapter_lifecycle


def get_counterfactual():
    global _counterfactual
    if _counterfactual is None:
        from explainability.counterfactual import CounterfactualExplainer

        _counterfactual = CounterfactualExplainer()
    return _counterfactual


def get_embedding_viz():
    global _embedding_viz
    if _embedding_viz is None:
        from explainability.embedding_viz import EmbeddingVisualizer

        _embedding_viz = EmbeddingVisualizer()
    return _embedding_viz


def get_distiller():
    global _distiller
    if _distiller is None:
        from training.knowledge_distillation import DistillationConfig, KnowledgeDistiller

        _distiller = KnowledgeDistiller(DistillationConfig())
    return _distiller


def get_gpu_scheduler():
    global _gpu_scheduler
    if _gpu_scheduler is None:
        from training.gpu_scheduler import GPUScheduler, SchedulerConfig

        _gpu_scheduler = GPUScheduler(SchedulerConfig())
        _gpu_scheduler.start()
    return _gpu_scheduler


def component_status() -> dict[str, bool]:
    """Report which lazy singletons have been loaded (used by /health)."""
    return {
        "lora_trainer": _lora_trainer is not None,
        "model_registry": _model_registry is not None,
        "rag_pipeline": _rag_pipeline is not None,
        "inference_service": _inference_service is not None,
        "conversational_pipeline": _conversational_pipeline is not None,
        "mlflow_tracker": _mlflow_tracker is not None,
        "e2e_pipeline": _e2e_pipeline is not None,
        "explainer_manager": _explainer_manager is not None,
        "knowledge_distiller": _distiller is not None,
        "gpu_scheduler": _gpu_scheduler is not None,
        "counterfactual": _counterfactual is not None,
        "embedding_viz": _embedding_viz is not None,
    }


def readiness_status() -> dict[str, bool]:
    """Report the critical components required for a readiness probe."""
    return {
        "controller": controller is not None,
        "signature_manager": sig_manager is not None,
        "lora_trainer": _lora_trainer is not None,
        "model_registry": _model_registry is not None,
        "inference_service": _inference_service is not None,
        "e2e_pipeline": _e2e_pipeline is not None,
    }
