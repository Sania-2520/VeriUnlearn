"""VeriUnlearn — Algorithm wrappers for unlearning benchmarking.

Provides a unified interface over five unlearning strategies implemented with
scikit-learn (LogisticRegression, MLPClassifier, SGDClassifier) for both
tabular/image and text (TF-IDF) datasets.  Every algorithm records training
time, unlearning time, and peak memory usage.

Strategies
----------
1. **Retrain** — Gold-standard: retrain from scratch on retained data.
2. **SISA** — Sharded Isolated Sliced Aggregated unlearning.
3. **SCRUB** — Student-teacher residual forgetting via soft-target matching.
4. **Influence Functions** — Gradient-based influence estimation and reweighting.
5. **Fine-Tune Forgetting** — Gradient-ascent forgetting + retain fine-tune.

All public classes inherit from ``UnlearningAlgorithm`` and expose the same
``fit / unlearn / evaluate / get_params`` contract.
"""

from __future__ import annotations

import abc
import copy
import logging
import os
import time
import tracemalloc
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.special import softmax as _scipy_softmax
from sklearn.base import BaseEstimator, clone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEXT_DATASETS = frozenset({"imdb", "ag_news", "sst2", "agnews"})
_IMAGE_DATASETS = frozenset({"mnist", "cifar10", "cifar-10"})


def _is_text_dataset(dataset_name: str) -> bool:
    return dataset_name.lower().replace("-", "_").replace(" ", "_") in _TEXT_DATASETS


def _is_image_dataset(dataset_name: str) -> bool:
    return dataset_name.lower().replace("-", "_").replace(" ", "_") in _IMAGE_DATASETS


def _timer() -> tuple[float, float]:
    """Return (start, wall) — call ``time.perf_counter()`` as *start*."""
    return time.perf_counter(), 0.0


def _elapsed(start: float) -> float:
    return time.perf_counter() - start


def _memory_context() -> tracemalloc.Snapshot | None:
    """Start tracing; caller must capture snapshot after work."""
    tracemalloc.start()
    return None


def _memory_peak_mb() -> float:
    """Stop tracing and return peak usage in MiB."""
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak / (1024 * 1024)


def _seed_everything(seed: int) -> None:
    np.random.seed(seed)


def _build_estimator(
    num_classes: int,
    is_text: bool,
    is_image: bool,
    *,
    extra_kwargs: dict[str, Any] | None = None,
) -> BaseEstimator:
    """Return a fresh estimator suited to the data modality."""
    kwargs = extra_kwargs or {}
    if is_text:
        return LogisticRegression(
            max_iter=kwargs.get("max_iter", 500),
            solver="lbfgs",
            C=kwargs.get("C", 1.0),
            random_state=kwargs.get("random_state", 42),
        )
    if num_classes > 10 or is_image:
        return MLPClassifier(
            hidden_layer_sizes=kwargs.get("hidden_layer_sizes", (128, 64)),
            max_iter=kwargs.get("max_iter", 100),
            early_stopping=True,
            validation_fraction=0.1,
            random_state=kwargs.get("random_state", 42),
        )
    return MLPClassifier(
        hidden_layer_sizes=kwargs.get("hidden_layer_sizes", (64, 32)),
        max_iter=kwargs.get("max_iter", 100),
        early_stopping=True,
        validation_fraction=0.1,
        random_state=kwargs.get("random_state", 42),
    )


# ---------------------------------------------------------------------------
# Data container
# ---------------------------------------------------------------------------


@dataclass
class EvalDataset:
    """Lightweight container for benchmark data."""

    X: np.ndarray
    y: np.ndarray
    X_test: np.ndarray
    y_test: np.ndarray
    dataset_name: str = ""
    is_text: bool = False
    is_image: bool = False
    texts: list[str] | None = None
    texts_test: list[str] | None = None


@dataclass
class TrainResult:
    """Output produced by ``fit``."""

    estimator: BaseEstimator
    vectorizer: TfidfVectorizer | None = None
    scaler: StandardScaler | None = None
    train_accuracy: float = 0.0
    val_accuracy: float = 0.0
    training_time_s: float = 0.0
    peak_memory_mb: float = 0.0


@dataclass
class UnlearnResult:
    """Output produced by ``unlearn``."""

    estimator: BaseEstimator
    vectorizer: TfidfVectorizer | None = None
    scaler: StandardScaler | None = None
    unlearning_time_s: float = 0.0
    peak_memory_mb: float = 0.0
    metrics: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class UnlearningAlgorithm(abc.ABC):
    """Unified interface every algorithm must satisfy."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Short human-readable name (e.g. ``'retrain'``)."""

    @abc.abstractmethod
    def fit(
        self,
        dataset: EvalDataset,
        *,
        seed: int = 42,
        **kwargs: Any,
    ) -> TrainResult:
        """Train the model on the *full* training data."""

    @abc.abstractmethod
    def unlearn(
        self,
        trained: TrainResult,
        forget_indices: np.ndarray,
        retain_indices: np.ndarray,
        dataset: EvalDataset,
        *,
        seed: int = 42,
        **kwargs: Any,
    ) -> UnlearnResult:
        """Produce a new model after forgetting the specified samples."""

    @abc.abstractmethod
    def evaluate(
        self,
        result: UnlearnResult | TrainResult,
        dataset: EvalDataset,
    ) -> dict[str, float]:
        """Compute a full metric dictionary on the test split."""

    @abc.abstractmethod
    def get_params(self) -> dict[str, Any]:
        """Algorithm-specific hyper-parameters."""


# ---------------------------------------------------------------------------
# 1. Retrain  (gold standard baseline)
# ---------------------------------------------------------------------------


class Retraining(UnlearningAlgorithm):
    """Retrain from scratch on the retained data only."""

    def __init__(self, *, max_iter: int = 300) -> None:
        self.max_iter = max_iter

    @property
    def name(self) -> str:
        return "retrain"

    def fit(
        self,
        dataset: EvalDataset,
        *,
        seed: int = 42,
        **kwargs: Any,
    ) -> TrainResult:
        _seed_everything(seed)
        estimator = _build_estimator(
            int(dataset.y.max()) + 1,
            dataset.is_text,
            dataset.is_image,
            extra_kwargs={"max_iter": self.max_iter, "random_state": seed},
        )

        scaler: StandardScaler | None = None
        vectorizer: TfidfVectorizer | None = None

        tracemalloc.start()
        t0 = time.perf_counter()

        if dataset.is_text and dataset.texts is not None:
            vectorizer = TfidfVectorizer(max_features=5000)
            X = vectorizer.fit_transform(dataset.texts)
            X_test = vectorizer.transform(dataset.texts_test)
        else:
            scaler = StandardScaler()
            X = scaler.fit_transform(dataset.X)
            X_test = scaler.transform(dataset.X_test)

        estimator.fit(X, dataset.y)
        train_time = time.perf_counter() - t0
        peak = _memory_peak_mb() if tracemalloc.is_tracing() else 0.0
        if tracemalloc.is_tracing():
            tracemalloc.stop()

        train_acc = accuracy_score(dataset.y, estimator.predict(X))
        val_acc = accuracy_score(dataset.y_test, estimator.predict(X_test))

        return TrainResult(
            estimator=estimator,
            vectorizer=vectorizer,
            scaler=scaler,
            train_accuracy=float(train_acc),
            val_accuracy=float(val_acc),
            training_time_s=float(train_time),
            peak_memory_mb=float(peak),
        )

    def unlearn(
        self,
        trained: TrainResult,
        forget_indices: np.ndarray,
        retain_indices: np.ndarray,
        dataset: EvalDataset,
        *,
        seed: int = 42,
        **kwargs: Any,
    ) -> UnlearnResult:
        _seed_everything(seed)
        retain_X = dataset.X[retain_indices]
        retain_y = dataset.y[retain_indices]

        estimator = _build_estimator(
            int(dataset.y.max()) + 1,
            dataset.is_text,
            dataset.is_image,
            extra_kwargs={"max_iter": self.max_iter, "random_state": seed},
        )

        scaler: StandardScaler | None = None
        vectorizer: TfidfVectorizer | None = None

        tracemalloc.start()
        t0 = time.perf_counter()

        if dataset.is_text and dataset.texts is not None:
            texts_retain = [dataset.texts[i] for i in retain_indices]
            vectorizer = TfidfVectorizer(max_features=5000)
            X = vectorizer.fit_transform(texts_retain)
        else:
            scaler = StandardScaler()
            X = scaler.fit_transform(retain_X)

        estimator.fit(X, retain_y)
        unlearn_time = time.perf_counter() - t0
        peak = _memory_peak_mb() if tracemalloc.is_tracing() else 0.0
        if tracemalloc.is_tracing():
            tracemalloc.stop()

        return UnlearnResult(
            estimator=estimator,
            vectorizer=vectorizer,
            scaler=scaler,
            unlearning_time_s=float(unlearn_time),
            peak_memory_mb=float(peak),
            metrics={"retained_samples": len(retain_indices), "method": "full_retrain"},
        )

    def evaluate(self, result: UnlearnResult | TrainResult, dataset: EvalDataset) -> dict[str, float]:
        X_test, y_test = self._transform_test(result, dataset)
        preds = result.estimator.predict(X_test)
        return _classification_metrics(dataset.y_test, preds)

    def get_params(self) -> dict[str, Any]:
        return {"max_iter": self.max_iter}

    @staticmethod
    def _transform_test(result: UnlearnResult | TrainResult, dataset: EvalDataset) -> tuple[Any, np.ndarray]:
        if result.vectorizer is not None and dataset.texts_test is not None:
            return result.vectorizer.transform(dataset.texts_test), dataset.y_test
        if result.scaler is not None:
            return result.scaler.transform(dataset.X_test), dataset.y_test
        return dataset.X_test, dataset.y_test


# ---------------------------------------------------------------------------
# 2. SISA — Sharded Isolated Sliced Aggregated
# ---------------------------------------------------------------------------


class _ShardedEnsemble:
    """Wraps SISA's per-shard models into a single sklearn-compatible estimator.

    Applies each shard's scaler/vectorizer before calling predict, then
    aggregates via majority vote.
    """
    def __init__(self, sisa: "SISA") -> None:
        self._sisa = sisa

    def predict(self, X: np.ndarray | list[str]) -> np.ndarray:
        n = len(X)
        votes: list[np.ndarray] = []
        for s_idx in range(self._sisa.num_shards):
            est = self._sisa._shard_models[s_idx]
            if est is None:
                votes.append(np.full(n, -1, dtype=int))
                continue
            vec = self._sisa._shard_vectorizers[s_idx]
            scl = self._sisa._shard_scalers[s_idx]
            if vec is not None:
                X_t = vec.transform(X)
            elif scl is not None:
                X_t = scl.transform(X)
            else:
                X_t = X
            votes.append(est.predict(X_t))
        votes_arr = np.array(votes)
        final = np.zeros(n, dtype=int)
        for i in range(n):
            valid = votes_arr[:, i][votes_arr[:, i] >= 0]
            if len(valid) > 0:
                final[i] = np.bincount(valid).argmax()
        return final

    def predict_proba(self, X: np.ndarray | list[str]) -> np.ndarray:
        n = len(X)
        probas: list[np.ndarray] = []
        for s_idx in range(self._sisa.num_shards):
            est = self._sisa._shard_models[s_idx]
            if est is None:
                continue
            vec = self._sisa._shard_vectorizers[s_idx]
            scl = self._sisa._shard_scalers[s_idx]
            if vec is not None:
                X_t = vec.transform(X)
            elif scl is not None:
                X_t = scl.transform(X)
            else:
                X_t = X
            probas.append(est.predict_proba(X_t))
        if not probas:
            return np.zeros((n, 2))
        return np.mean(probas, axis=0)


class SISA(UnlearningAlgorithm):
    """Sharded Isolated Sliced Aggregated unlearning.

    Splits the training data into *K* shards, trains an independent model per
    shard, and only retrains the shard(s) that contain forget samples.
    """

    def __init__(self, *, num_shards: int = 5, max_iter: int = 300) -> None:
        self.num_shards = num_shards
        self.max_iter = max_iter

    @property
    def name(self) -> str:
        return "sisa"

    def fit(
        self,
        dataset: EvalDataset,
        *,
        seed: int = 42,
        **kwargs: Any,
    ) -> TrainResult:
        _seed_everything(seed)
        n = len(dataset.y)
        shard_models: list[BaseEstimator] = []
        shard_vectorizers: list[TfidfVectorizer | None] = []
        shard_scalers: list[StandardScaler | None] = []

        indices = np.arange(n)
        rng = np.random.RandomState(seed)
        rng.shuffle(indices)
        shards = np.array_split(indices, self.num_shards)

        tracemalloc.start()
        t0 = time.perf_counter()

        for shard_idx in range(self.num_shards):
            shard_idx_arr = shards[shard_idx]
            if len(shard_idx_arr) == 0:
                shard_models.append(None)  # type: ignore[arg-type]
                shard_vectorizers.append(None)
                shard_scalers.append(None)
                continue

            est = _build_estimator(
                int(dataset.y.max()) + 1,
                dataset.is_text,
                dataset.is_image,
                extra_kwargs={"max_iter": self.max_iter, "random_state": seed + shard_idx},
            )
            vec: TfidfVectorizer | None = None
            scl: StandardScaler | None = None

            if dataset.is_text and dataset.texts is not None:
                vec = TfidfVectorizer(max_features=5000)
                texts_shard = [dataset.texts[i] for i in shard_idx_arr]
                X_s = vec.fit_transform(texts_shard)
            else:
                scl = StandardScaler()
                X_s = scl.fit_transform(dataset.X[shard_idx_arr])

            est.fit(X_s, dataset.y[shard_idx_arr])
            shard_models.append(est)
            shard_vectorizers.append(vec)
            shard_scalers.append(scl)

        train_time = time.perf_counter() - t0
        peak = _memory_peak_mb() if tracemalloc.is_tracing() else 0.0
        if tracemalloc.is_tracing():
            tracemalloc.stop()

        self._shard_models = shard_models
        self._shard_vectorizers = shard_vectorizers
        self._shard_scalers = shard_scalers
        self._shards = shards
        self._num_classes = int(dataset.y.max()) + 1

        X_test = self._transform_test_aggregated(dataset)
        all_preds = self._predict_aggregated(X_test)
        val_acc = accuracy_score(dataset.y_test, all_preds)

        return TrainResult(
            estimator=_ShardedEnsemble(self),
            vectorizer=None,
            scaler=None,
            train_accuracy=0.0,
            val_accuracy=float(val_acc),
            training_time_s=float(train_time),
            peak_memory_mb=float(peak),
        )

    def unlearn(
        self,
        trained: TrainResult,
        forget_indices: np.ndarray,
        retain_indices: np.ndarray,
        dataset: EvalDataset,
        *,
        seed: int = 42,
        **kwargs: Any,
    ) -> UnlearnResult:
        _seed_everything(seed)
        shards = self._shards

        affected: set[int] = set()
        for idx in forget_indices:
            for s_idx, shard_arr in enumerate(shards):
                if idx in shard_arr:
                    affected.add(s_idx)
                    break

        tracemalloc.start()
        t0 = time.perf_counter()

        for s_idx in affected:
            shard_arr = shards[s_idx]
            remaining_in_shard = np.array([i for i in shard_arr if i not in set(forget_indices)])
            if len(remaining_in_shard) == 0:
                self._shard_models[s_idx] = None  # type: ignore[assignment]
                continue

            est = _build_estimator(
                self._num_classes,
                dataset.is_text,
                dataset.is_image,
                extra_kwargs={"max_iter": self.max_iter, "random_state": seed + s_idx},
            )
            vec: TfidfVectorizer | None = None
            scl: StandardScaler | None = None

            if dataset.is_text and dataset.texts is not None:
                vec = TfidfVectorizer(max_features=5000)
                texts_shard = [dataset.texts[i] for i in remaining_in_shard]
                X_s = vec.fit_transform(texts_shard)
            else:
                scl = StandardScaler()
                X_s = scl.fit_transform(dataset.X[remaining_in_shard])

            est.fit(X_s, dataset.y[remaining_in_shard])
            self._shard_models[s_idx] = est
            self._shard_vectorizers[s_idx] = vec
            self._shard_scalers[s_idx] = scl

        unlearn_time = time.perf_counter() - t0
        peak = _memory_peak_mb() if tracemalloc.is_tracing() else 0.0
        if tracemalloc.is_tracing():
            tracemalloc.stop()

        X_test = self._transform_test_aggregated(dataset)
        post_preds = self._predict_aggregated(X_test)

        return UnlearnResult(
            estimator=_ShardedEnsemble(self),
            vectorizer=None,
            scaler=None,
            unlearning_time_s=float(unlearn_time),
            peak_memory_mb=float(peak),
            metrics={
                "shards_affected": len(affected),
                "total_shards": self.num_shards,
            },
        )

    def evaluate(self, result: UnlearnResult | TrainResult, dataset: EvalDataset) -> dict[str, float]:
        X_test = self._transform_test_aggregated(dataset)
        preds = self._predict_aggregated(X_test)
        return _classification_metrics(dataset.y_test, preds)

    def get_params(self) -> dict[str, Any]:
        return {"num_shards": self.num_shards, "max_iter": self.max_iter}

    def _transform_test_aggregated(self, dataset: EvalDataset) -> Any:
        """Transform test data through each shard's transformer and stack."""
        parts: list[Any] = []
        n_test = len(dataset.y_test)
        shard_preds_all: list[np.ndarray] = []
        for s_idx in range(self.num_shards):
            est = self._shard_models[s_idx]
            if est is None:
                shard_preds_all.append(np.full(n_test, -1, dtype=int))
                continue
            if self._shard_vectorizers[s_idx] is not None and dataset.texts_test is not None:
                X_t = self._shard_vectorizers[s_idx].transform(dataset.texts_test)
            elif self._shard_scalers[s_idx] is not None:
                X_t = self._shard_scalers[s_idx].transform(dataset.X_test)
            else:
                X_t = dataset.X_test
            shard_preds_all.append(est.predict(X_t))
        return np.stack(shard_preds_all)  # (num_shards, n_test)

    def _predict_aggregated(self, shard_preds: Any) -> np.ndarray:
        """Majority-vote aggregation across shards."""
        n_test = shard_preds.shape[1]
        final = np.zeros(n_test, dtype=int)
        for i in range(n_test):
            votes = shard_preds[:, i]
            valid = votes[votes >= 0]
            if len(valid) == 0:
                final[i] = 0
            else:
                vals, counts = np.unique(valid, return_counts=True)
                final[i] = vals[np.argmax(counts)]
        return final


# ---------------------------------------------------------------------------
# 3. SCRUB — Student-teacher residual forgetting
# ---------------------------------------------------------------------------


class SCRUB(UnlearningAlgorithm):
    """Student-teacher residual forgetting via pseudo-label distillation.

    After initial training the *original* model acts as the frozen teacher.
    A student model is trained to:
      * **Forget**: maximise divergence from the teacher on forget data
        (soft-target MSE).
      * **Retain**: minimise divergence from the teacher on retain data
        (soft-target MSE) while also minimising cross-entropy on retain labels.
    """

    def __init__(
        self,
        *,
        max_iter: int = 200,
        forget_weight: float = 1.0,
        retain_weight: float = 1.0,
        temperature: float = 2.0,
    ) -> None:
        self.max_iter = max_iter
        self.forget_weight = forget_weight
        self.retain_weight = retain_weight
        self.temperature = temperature

    @property
    def name(self) -> str:
        return "scrub"

    def fit(
        self,
        dataset: EvalDataset,
        *,
        seed: int = 42,
        **kwargs: Any,
    ) -> TrainResult:
        _seed_everything(seed)
        estimator = _build_estimator(
            int(dataset.y.max()) + 1,
            dataset.is_text,
            dataset.is_image,
            extra_kwargs={"max_iter": self.max_iter, "random_state": seed},
        )

        scaler: StandardScaler | None = None
        vectorizer: TfidfVectorizer | None = None

        tracemalloc.start()
        t0 = time.perf_counter()

        if dataset.is_text and dataset.texts is not None:
            vectorizer = TfidfVectorizer(max_features=5000)
            X = vectorizer.fit_transform(dataset.texts)
            X_test = vectorizer.transform(dataset.texts_test)
        else:
            scaler = StandardScaler()
            X = scaler.fit_transform(dataset.X)
            X_test = scaler.transform(dataset.X_test)

        estimator.fit(X, dataset.y)
        train_time = time.perf_counter() - t0
        peak = _memory_peak_mb() if tracemalloc.is_tracing() else 0.0
        if tracemalloc.is_tracing():
            tracemalloc.stop()

        self._teacher = clone(estimator)
        self._teacher.fit(X, dataset.y)  # frozen teacher

        train_acc = accuracy_score(dataset.y, estimator.predict(X))
        val_acc = accuracy_score(dataset.y_test, estimator.predict(X_test))

        return TrainResult(
            estimator=estimator,
            vectorizer=vectorizer,
            scaler=scaler,
            train_accuracy=float(train_acc),
            val_accuracy=float(val_acc),
            training_time_s=float(train_time),
            peak_memory_mb=float(peak),
        )

    def unlearn(
        self,
        trained: TrainResult,
        forget_indices: np.ndarray,
        retain_indices: np.ndarray,
        dataset: EvalDataset,
        *,
        seed: int = 42,
        **kwargs: Any,
    ) -> UnlearnResult:
        _seed_everything(seed)
        teacher = self._teacher

        if dataset.is_text and trained.vectorizer is not None:
            X_forget = trained.vectorizer.transform([dataset.texts[i] for i in forget_indices])
            X_retain = trained.vectorizer.transform([dataset.texts[i] for i in retain_indices])
            X_test_t = trained.vectorizer.transform(dataset.texts_test)
        elif trained.scaler is not None:
            X_forget = trained.scaler.transform(dataset.X[forget_indices])
            X_retain = trained.scaler.transform(dataset.X[retain_indices])
            X_test_t = trained.scaler.transform(dataset.X_test)
        else:
            X_forget = dataset.X[forget_indices]
            X_retain = dataset.X[retain_indices]
            X_test_t = dataset.X_test

        teacher_forget = teacher.predict_proba(X_forget)
        teacher_retain = teacher.predict_proba(X_retain)

        tracemalloc.start()
        t0 = time.perf_counter()

        n_iter_sgd = max(1, self.max_iter // 2)
        num_classes = self._num_classes_retain(dataset)
        student = SGDClassifier(
            loss="log_loss",
            max_iter=1,
            warm_start=True,
            random_state=seed,
            eta0=0.01,
        )

        rng = np.random.RandomState(seed)
        y_retain_true = dataset.y[retain_indices]
        classes = np.arange(num_classes)

        init_n = min(100, len(retain_indices))
        student.fit(X_retain[:init_n], y_retain_true[:init_n])

        for _ in range(n_iter_sgd):
            indices_retain = np.arange(len(retain_indices))
            rng.shuffle(indices_retain)
            batch_re = indices_retain[: min(256, len(indices_retain))]
            X_re = X_retain[batch_re]
            pred_re = student.predict_proba(X_re)
            teacher_re = teacher_retain[batch_re]
            soft_target = (1 - self.retain_weight) * pred_re + self.retain_weight * teacher_re
            hard_labels = np.argmax(soft_target, axis=1)
            student.partial_fit(X_re, hard_labels, classes=classes)

            if len(forget_indices) > 0:
                indices_forget = np.arange(len(forget_indices))
                rng.shuffle(indices_forget)
                batch_fo = indices_forget[: min(256, len(indices_forget))]
                X_fo = X_forget[batch_fo]
                teacher_fo = teacher_forget[batch_fo]
                pred_fo = student.predict_proba(X_fo)
                diverge_target = 2.0 * teacher_fo - pred_fo
                diverge_labels = np.argmax(diverge_target, axis=1)
                student.partial_fit(X_fo, diverge_labels, classes=classes)

        unlearn_time = time.perf_counter() - t0
        peak = _memory_peak_mb() if tracemalloc.is_tracing() else 0.0
        if tracemalloc.is_tracing():
            tracemalloc.stop()

        post_preds = student.predict(X_test_t)
        val_acc = accuracy_score(dataset.y_test, post_preds)

        return UnlearnResult(
            estimator=student,
            vectorizer=trained.vectorizer,
            scaler=trained.scaler,
            unlearning_time_s=float(unlearn_time),
            peak_memory_mb=float(peak),
            metrics={"post_unlearn_accuracy": float(val_acc)},
        )

    def evaluate(self, result: UnlearnResult | TrainResult, dataset: EvalDataset) -> dict[str, float]:
        X_test, y_test = Retraining._transform_test(result, dataset)
        preds = result.estimator.predict(X_test)
        return _classification_metrics(dataset.y_test, preds)

    def get_params(self) -> dict[str, Any]:
        return {
            "max_iter": self.max_iter,
            "forget_weight": self.forget_weight,
            "retain_weight": self.retain_weight,
            "temperature": self.temperature,
        }

    @staticmethod
    def _num_classes_retain(dataset: EvalDataset) -> int:
        return int(dataset.y.max()) + 1


# ---------------------------------------------------------------------------
# 4. Influence Functions
# ---------------------------------------------------------------------------


class InfluenceFunctions(UnlearningAlgorithm):
    """Gradient-based influence estimation and correction.

    Approximates the effect of removing each training point by computing a
    per-sample influence score via Hessian-vector products (diagonal approx),
    then retrains on a re-weighted retain set.
    """

    def __init__(
        self,
        *,
        max_iter: int = 300,
        damping: float = 0.01,
        top_k_influences: int | None = None,
    ) -> None:
        self.max_iter = max_iter
        self.damping = damping
        self.top_k_influences = top_k_influences

    @property
    def name(self) -> str:
        return "influence_functions"

    def fit(
        self,
        dataset: EvalDataset,
        *,
        seed: int = 42,
        **kwargs: Any,
    ) -> TrainResult:
        _seed_everything(seed)
        estimator = _build_estimator(
            int(dataset.y.max()) + 1,
            dataset.is_text,
            dataset.is_image,
            extra_kwargs={"max_iter": self.max_iter, "random_state": seed},
        )

        scaler: StandardScaler | None = None
        vectorizer: TfidfVectorizer | None = None

        tracemalloc.start()
        t0 = time.perf_counter()

        if dataset.is_text and dataset.texts is not None:
            vectorizer = TfidfVectorizer(max_features=5000)
            X = vectorizer.fit_transform(dataset.texts)
            X_test = vectorizer.transform(dataset.texts_test)
        else:
            scaler = StandardScaler()
            X = scaler.fit_transform(dataset.X)
            X_test = scaler.transform(dataset.X_test)

        estimator.fit(X, dataset.y)
        train_time = time.perf_counter() - t0
        peak = _memory_peak_mb() if tracemalloc.is_tracing() else 0.0
        if tracemalloc.is_tracing():
            tracemalloc.stop()

        self._X_train = X
        self._y_train = dataset.y.copy()

        train_acc = accuracy_score(dataset.y, estimator.predict(X))
        val_acc = accuracy_score(dataset.y_test, estimator.predict(X_test))

        return TrainResult(
            estimator=estimator,
            vectorizer=vectorizer,
            scaler=scaler,
            train_accuracy=float(train_acc),
            val_accuracy=float(val_acc),
            training_time_s=float(train_time),
            peak_memory_mb=float(peak),
        )

    def unlearn(
        self,
        trained: TrainResult,
        forget_indices: np.ndarray,
        retain_indices: np.ndarray,
        dataset: EvalDataset,
        *,
        seed: int = 42,
        **kwargs: Any,
    ) -> UnlearnResult:
        _seed_everything(seed)

        if trained.vectorizer is not None and dataset.texts is not None:
            X_all = trained.vectorizer.transform(dataset.texts)
            X_test_t = trained.vectorizer.transform(dataset.texts_test)
        elif trained.scaler is not None:
            X_all = trained.scaler.transform(dataset.X)
            X_test_t = trained.scaler.transform(dataset.X_test)
        else:
            X_all = self._X_train
            X_test_t = dataset.X_test

        tracemalloc.start()
        t0 = time.perf_counter()

        weights = self._compute_influence_weights(
            trained.estimator, X_all, dataset.y, forget_indices, retain_indices
        )

        retain_X = X_all[retain_indices]
        retain_y = dataset.y[retain_indices]
        retain_w = weights[retain_indices]

        reweighted_estimator = _build_estimator(
            int(dataset.y.max()) + 1,
            dataset.is_text,
            dataset.is_image,
            extra_kwargs={"max_iter": self.max_iter, "random_state": seed},
        )

        sample_weights = np.clip(retain_w, 0.01, 10.0)
        reweighted_estimator.fit(retain_X, retain_y)

        try:
            reweighted_estimator.fit(retain_X, retain_y, sample_weight=sample_weights)
        except TypeError:
            reweighted_estimator.fit(retain_X, retain_y)

        unlearn_time = time.perf_counter() - t0
        peak = _memory_peak_mb() if tracemalloc.is_tracing() else 0.0
        if tracemalloc.is_tracing():
            tracemalloc.stop()

        post_preds = reweighted_estimator.predict(X_test_t)
        val_acc = accuracy_score(dataset.y_test, post_preds)

        return UnlearnResult(
            estimator=reweighted_estimator,
            vectorizer=trained.vectorizer,
            scaler=trained.scaler,
            unlearning_time_s=float(unlearn_time),
            peak_memory_mb=float(peak),
            metrics={
                "post_unlearn_accuracy": float(val_acc),
                "damping": self.damping,
                "mean_weight": float(np.mean(sample_weights)),
            },
        )

    def evaluate(self, result: UnlearnResult | TrainResult, dataset: EvalDataset) -> dict[str, float]:
        X_test, _ = Retraining._transform_test(result, dataset)
        preds = result.estimator.predict(X_test)
        return _classification_metrics(dataset.y_test, preds)

    def get_params(self) -> dict[str, Any]:
        return {
            "max_iter": self.max_iter,
            "damping": self.damping,
            "top_k_influences": self.top_k_influences,
        }

    def _compute_influence_weights(
        self,
        estimator: BaseEstimator,
        X_all: Any,
        y_all: np.ndarray,
        forget_indices: np.ndarray,
        retain_indices: np.ndarray,
    ) -> np.ndarray:
        """Compute per-sample influence weights.

        For a logistic / linear model the influence of training point *i* on
        the loss at test point *z* can be approximated as:

            I(z, z_i) = - H^{-1} ∇ℓ(z_i) · ∇ℓ(z)

        We use a diagonal approximation of the Hessian and pre-compute the
        gradient of the forget set, then score every retain point.
        """
        n_train = X_all.shape[0]
        weights = np.ones(n_train, dtype=np.float64)

        try:
            if hasattr(estimator, "coef_") and estimator.coef_ is not None:
                coef = estimator.coef_
                if coef.ndim > 1:
                    coef_mean = coef.mean(axis=0)
                else:
                    coef_mean = coef.ravel()
            else:
                return weights

            X_forget_dense = X_all[forget_indices].toarray() if hasattr(X_all[forget_indices], "toarray") else np.asarray(X_all[forget_indices])
            X_retain_dense = X_all[retain_indices].toarray() if hasattr(X_all[retain_indices], "toarray") else np.asarray(X_all[retain_indices])

            pred_forget = estimator.predict_proba(X_all[forget_indices])
            y_forget_oh = np.zeros_like(pred_forget)
            for idx, lbl in enumerate(dataset.y_forget if hasattr(self, "_y_forget") else y_all[forget_indices]):
                y_forget_oh[idx, int(lbl)] = 1.0
            grad_forget = (pred_forget - y_forget_oh).mean(axis=0)

            diag_hessian = np.abs(X_retain_dense).mean(axis=0) * np.abs(coef_mean) + self.damping
            diag_hessian = np.maximum(diag_hessian, self.damping)

            influence_scores = np.zeros(len(retain_indices), dtype=np.float64)
            for j in range(len(retain_indices)):
                x_j = X_retain_dense[j]
                pred_j = estimator.predict_proba(X_all[retain_indices[j] : retain_indices[j] + 1])[0]
                y_j_oh = np.zeros_like(pred_j)
                y_j_oh[int(y_all[retain_indices[j]])] = 1.0
                grad_j = pred_j - y_j_oh
                hvp = diag_hessian * x_j
                inv_hvp = grad_j / (hvp + 1e-10)
                influence_scores[j] = float(np.dot(inv_hvp, grad_forget))

            if self.top_k_influences is not None:
                k = min(self.top_k_influences, len(retain_indices))
                threshold = np.sort(influence_scores)[k]
                mask = influence_scores <= threshold
                w = np.ones(len(retain_indices), dtype=np.float64)
                w[~mask] = 0.1
            else:
                w = 1.0 / (1.0 + np.abs(influence_scores) * 10.0)

            for j, r_idx in enumerate(retain_indices):
                weights[r_idx] = w[j]

        except Exception:
            logger.debug("Influence weight computation fell back to uniform weights.", exc_info=True)

        return weights


# ---------------------------------------------------------------------------
# 5. Fine-Tune Forgetting (gradient ascent + retain fine-tune)
# ---------------------------------------------------------------------------


class FineTuneForgetting(UnlearningAlgorithm):
    """Gradient ascent on forget set + fine-tune on retain set.

    Uses SGDClassifier with partial_fit to simulate gradient ascent
    (increasing loss on forget set) followed by gradient descent on
    the retain set.
    """

    def __init__(
        self,
        *,
        ascent_epochs: int = 3,
        retain_epochs: int = 5,
        ascent_lr: float = 0.01,
        retain_lr: float = 0.005,
        batch_size: int = 256,
    ) -> None:
        self.ascent_epochs = ascent_epochs
        self.retain_epochs = retain_epochs
        self.ascent_lr = ascent_lr
        self.retain_lr = retain_lr
        self.batch_size = batch_size

    @property
    def name(self) -> str:
        return "fine_tune_forgetting"

    def fit(
        self,
        dataset: EvalDataset,
        *,
        seed: int = 42,
        **kwargs: Any,
    ) -> TrainResult:
        _seed_everything(seed)
        estimator = _build_estimator(
            int(dataset.y.max()) + 1,
            dataset.is_text,
            dataset.is_image,
            extra_kwargs={"max_iter": 300, "random_state": seed},
        )

        scaler: StandardScaler | None = None
        vectorizer: TfidfVectorizer | None = None

        tracemalloc.start()
        t0 = time.perf_counter()

        if dataset.is_text and dataset.texts is not None:
            vectorizer = TfidfVectorizer(max_features=5000)
            X = vectorizer.fit_transform(dataset.texts)
            X_test = vectorizer.transform(dataset.texts_test)
        else:
            scaler = StandardScaler()
            X = scaler.fit_transform(dataset.X)
            X_test = scaler.transform(dataset.X_test)

        estimator.fit(X, dataset.y)
        train_time = time.perf_counter() - t0
        peak = _memory_peak_mb() if tracemalloc.is_tracing() else 0.0
        if tracemalloc.is_tracing():
            tracemalloc.stop()

        self._pre_fit_X = X
        self._pre_fit_y = dataset.y.copy()

        train_acc = accuracy_score(dataset.y, estimator.predict(X))
        val_acc = accuracy_score(dataset.y_test, estimator.predict(X_test))

        return TrainResult(
            estimator=estimator,
            vectorizer=vectorizer,
            scaler=scaler,
            train_accuracy=float(train_acc),
            val_accuracy=float(val_acc),
            training_time_s=float(train_time),
            peak_memory_mb=float(peak),
        )

    def unlearn(
        self,
        trained: TrainResult,
        forget_indices: np.ndarray,
        retain_indices: np.ndarray,
        dataset: EvalDataset,
        *,
        seed: int = 42,
        **kwargs: Any,
    ) -> UnlearnResult:
        _seed_everything(seed)

        if trained.vectorizer is not None and dataset.texts is not None:
            X_forget = trained.vectorizer.transform([dataset.texts[i] for i in forget_indices])
            X_retain = trained.vectorizer.transform([dataset.texts[i] for i in retain_indices])
            X_test_t = trained.vectorizer.transform(dataset.texts_test)
        elif trained.scaler is not None:
            X_forget = trained.scaler.transform(dataset.X[forget_indices])
            X_retain = trained.scaler.transform(dataset.X[retain_indices])
            X_test_t = trained.scaler.transform(dataset.X_test)
        else:
            X_forget = self._pre_fit_X[forget_indices]
            X_retain = self._pre_fit_X[retain_indices]
            X_test_t = dataset.X_test

        num_classes = int(dataset.y.max()) + 1
        y_retain = dataset.y[retain_indices]

        tracemalloc.start()
        t0 = time.perf_counter()

        sgd = SGDClassifier(
            loss="log_loss",
            max_iter=1,
            warm_start=True,
            random_state=seed,
            eta0=self.ascent_lr,
        )
        classes = np.arange(num_classes)
        n_init = X_retain.shape[0] if hasattr(X_retain, "shape") else len(retain_indices)
        if hasattr(X_retain, "toarray"):
            init_X = X_retain[: min(100, n_init)]
            init_y = y_retain[: min(100, n_init)]
        else:
            init_X = X_retain[: min(100, n_init)]
            init_y = y_retain[: min(100, n_init)]
        sgd.fit(init_X, init_y)

        rng = np.random.RandomState(seed)

        for _ in range(self.ascent_epochs):
            if len(forget_indices) == 0:
                break
            indices = np.arange(len(forget_indices))
            rng.shuffle(indices)
            for start in range(0, len(indices), self.batch_size):
                batch_idx = indices[start : start + self.batch_size]
                X_b = X_forget[batch_idx]
                proba = sgd.predict_proba(X_b)
                flipped_labels = np.argmax(1.0 - proba, axis=1)
                sgd.partial_fit(X_b, flipped_labels, classes=classes)

        for _ in range(self.retain_epochs):
            indices = np.arange(len(retain_indices))
            rng.shuffle(indices)
            for start in range(0, len(indices), self.batch_size):
                batch_idx = indices[start : start + self.batch_size]
                X_b = X_retain[batch_idx]
                y_b = y_retain[batch_idx]
                sgd.partial_fit(X_b, y_b, classes=classes)

        unlearn_time = time.perf_counter() - t0
        peak = _memory_peak_mb() if tracemalloc.is_tracing() else 0.0
        if tracemalloc.is_tracing():
            tracemalloc.stop()

        post_preds = sgd.predict(X_test_t)
        val_acc = accuracy_score(dataset.y_test, post_preds)

        return UnlearnResult(
            estimator=sgd,
            vectorizer=trained.vectorizer,
            scaler=trained.scaler,
            unlearning_time_s=float(unlearn_time),
            peak_memory_mb=float(peak),
            metrics={"post_unlearn_accuracy": float(val_acc)},
        )

    def evaluate(self, result: UnlearnResult | TrainResult, dataset: EvalDataset) -> dict[str, float]:
        X_test, _ = Retraining._transform_test(result, dataset)
        preds = result.estimator.predict(X_test)
        return _classification_metrics(dataset.y_test, preds)

    def get_params(self) -> dict[str, Any]:
        return {
            "ascent_epochs": self.ascent_epochs,
            "retain_epochs": self.retain_epochs,
            "ascent_lr": self.ascent_lr,
            "retain_lr": self.retain_lr,
            "batch_size": self.batch_size,
        }


# ---------------------------------------------------------------------------
# Shared metric helpers
# ---------------------------------------------------------------------------


def _classification_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """Return a standard classification metric dict."""
    num_classes = int(max(y_true.max(), y_pred.max())) + 1
    acc = float(accuracy_score(y_true, y_pred))
    return {
        "accuracy": acc,
        "precision_macro": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "precision_weighted": float(precision_score(y_true, y_pred, average="weighted", zero_division=0)),
        "recall_macro": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "recall_weighted": float(recall_score(y_true, y_pred, average="weighted", zero_division=0)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_weighted": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
    }


# ---------------------------------------------------------------------------
# Factory / registry
# ---------------------------------------------------------------------------

ALGORITHM_REGISTRY: dict[str, type[UnlearningAlgorithm]] = {
    "retrain": Retraining,
    "sisa": SISA,
    "scrub": SCRUB,
    "influence_functions": InfluenceFunctions,
    "fine_tune_forgetting": FineTuneForgetting,
}


def get_algorithm(name: str, **kwargs: Any) -> UnlearningAlgorithm:
    """Instantiate an algorithm by name."""
    cls = ALGORITHM_REGISTRY.get(name)
    if cls is None:
        raise ValueError(f"Unknown algorithm '{name}'. Choose from: {list(ALGORITHM_REGISTRY)}")
    return cls(**kwargs)


def list_algorithms() -> list[str]:
    """Return sorted list of registered algorithm names."""
    return sorted(ALGORITHM_REGISTRY.keys())
