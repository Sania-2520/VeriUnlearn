"""VeriUnlearn — Comprehensive metric computation suite for unlearning evaluation.

Provides ``MetricsComputer`` (per-experiment) and ``aggregate_results`` /
``compute_statistical_significance`` helpers for cross-run aggregation.
All functions are self-contained and depend only on numpy, scipy, and sklearn.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy import stats as _scipy_stats
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix as _sk_confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve as _sk_roc_curve,
    average_precision_score,
)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Classification metrics
# ═══════════════════════════════════════════════════════════════════════════


def compute_classification_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    num_classes: int | None = None,
) -> dict[str, float]:
    """Accuracy, precision, recall, F1 — per-class + macro + weighted.

    Returns
    -------
    dict with keys:
        accuracy, precision_macro, recall_macro, f1_macro,
        precision_weighted, recall_weighted, f1_weighted,
        precision_per_class_<i>, recall_per_class_<i>, f1_per_class_<i>
    """
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    if num_classes is None:
        num_classes = int(max(y_true.max(), y_pred.max())) + 1

    result: dict[str, float] = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "precision_weighted": float(precision_score(y_true, y_pred, average="weighted", zero_division=0)),
        "recall_macro": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "recall_weighted": float(recall_score(y_true, y_pred, average="weighted", zero_division=0)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_weighted": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
    }

    for c in range(num_classes):
        mask_true = (y_true == c).astype(int)
        mask_pred = (y_pred == c).astype(int)
        tp = int(((mask_true == 1) & (mask_pred == 1)).sum())
        fp = int(((mask_true == 0) & (mask_pred == 1)).sum())
        fn = int(((mask_true == 1) & (mask_pred == 0)).sum())
        p = tp / max(tp + fp, 1)
        r = tp / max(tp + fn, 1)
        f1 = 2 * p * r / max(p + r, 1e-12)
        result[f"precision_per_class_{c}"] = float(p)
        result[f"recall_per_class_{c}"] = float(r)
        result[f"f1_per_class_{c}"] = float(f1)

    return result


# ═══════════════════════════════════════════════════════════════════════════
# 2. Forget quality
# ═══════════════════════════════════════════════════════════════════════════


def compute_forget_quality(
    acc_before_forget: float,
    acc_after_forget: float,
    loss_member: np.ndarray,
    loss_nonmember: np.ndarray,
) -> dict[str, float]:
    """How well the model *forgot* the target data.

    Metrics
    -------
    forget_accuracy_before  – accuracy on forget set *before* unlearning
    forget_accuracy_after   – accuracy on forget set *after* unlearning
    forget_drop             – before – after (higher → better forgetting)
    memorization_score      – mean(loss_member) - mean(loss_nonmember)
                             (positive → model memorised; ideally ≤ 0 after unlearning)
    """
    forget_acc_drop = acc_before_forget - acc_after_forget

    loss_member = np.asarray(loss_member, dtype=np.float64)
    loss_nonmember = np.asarray(loss_nonmember, dtype=np.float64)

    mem_loss = float(np.mean(loss_member)) if len(loss_member) > 0 else 0.0
    non_mem_loss = float(np.mean(loss_nonmember)) if len(loss_nonmember) > 0 else 0.0
    memorization = mem_loss - non_mem_loss

    return {
        "forget_accuracy_before": float(acc_before_forget),
        "forget_accuracy_after": float(acc_after_forget),
        "forget_drop": float(forget_acc_drop),
        "memorization_score": float(memorization),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 3. Utility metrics
# ═══════════════════════════════════════════════════════════════════════════


def compute_utility_metrics(
    accuracy_before_test: float,
    accuracy_after_test: float,
    accuracy_before_retain: float,
    accuracy_after_retain: float,
) -> dict[str, float]:
    """How well the model retains useful knowledge.

    Metrics
    -------
    utility_loss          – accuracy_before_test – accuracy_after_test
                           (lower → less utility lost)
    knowledge_retention   – accuracy_after_retain / max(accuracy_before_retain, 1e-12)
                           (closer to 1 → better retention)
    """
    utility_loss = accuracy_before_test - accuracy_after_test
    knowledge_retention = accuracy_after_retain / max(accuracy_before_retain, 1e-12)

    return {
        "utility_loss": float(utility_loss),
        "knowledge_retention": float(min(max(knowledge_retention, 0.0), 2.0)),
        "accuracy_test_before": float(accuracy_before_test),
        "accuracy_test_after": float(accuracy_after_test),
        "accuracy_retain_before": float(accuracy_before_retain),
        "accuracy_retain_after": float(accuracy_after_retain),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 4. Privacy metrics
# ═══════════════════════════════════════════════════════════════════════════


def compute_privacy_metrics(
    member_losses: np.ndarray,
    nonmember_losses: np.ndarray,
    member_correct: np.ndarray | None = None,
    nonmember_correct: np.ndarray | None = None,
    threshold_percentile: float = 50.0,
) -> dict[str, float]:
    """Membership-inference and privacy-leakage metrics.

    Uses a loss-threshold MIA: samples whose loss is below a percentile
    threshold of the *non-member* distribution are predicted as members.

    Metrics
    -------
    mia_attack_accuracy   – overall accuracy of the threshold-based MIA
    mia_attack_auroc      – area under ROC for the loss-based MIA
    privacy_leakage_score – (1 - AUROC)  — lower leakage = higher score
    overfitting_gap       – max(0, mean_member_loss − mean_nonmember_loss) normalised
    """
    member_losses = np.asarray(member_losses, dtype=np.float64)
    nonmember_losses = np.asarray(nonmember_losses, dtype=np.float64)

    if len(member_losses) == 0 or len(nonmember_losses) == 0:
        return {
            "mia_attack_accuracy": 0.5,
            "mia_attack_auroc": 0.5,
            "privacy_leakage_score": 0.5,
            "overfitting_gap": 0.0,
        }

    all_losses = np.concatenate([member_losses, nonmember_losses])
    threshold = float(np.percentile(all_losses, threshold_percentile))

    member_preds_member = (member_losses <= threshold).astype(int)
    nonmember_preds_member = (nonmember_losses <= threshold).astype(int)

    correct = np.concatenate([
        member_preds_member,
        1 - nonmember_preds_member,
    ])
    mia_accuracy = float(np.mean(correct))

    labels = np.concatenate([
        np.ones(len(member_losses), dtype=int),
        np.zeros(len(nonmember_losses), dtype=int),
    ])
    scores = -all_losses  # lower loss → higher membership probability

    try:
        auroc = float(roc_auc_score(labels, scores))
    except ValueError:
        auroc = 0.5

    privacy_leakage = 1.0 - auroc

    mean_m = float(np.mean(member_losses))
    mean_nm = float(np.mean(nonmember_losses))
    overfitting = max(0.0, mean_m - mean_nm)
    normalisation = max(abs(mean_m), abs(mean_nm), 1e-12)
    overfitting_gap = overfitting / normalisation

    return {
        "mia_attack_accuracy": float(mia_accuracy),
        "mia_attack_auroc": float(auroc),
        "privacy_leakage_score": float(privacy_leakage),
        "overfitting_gap": float(overfitting_gap),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 5. Efficiency metrics
# ═══════════════════════════════════════════════════════════════════════════


def compute_efficiency_metrics(
    training_time_s: float,
    unlearning_time_s: float,
    retraining_time_s: float,
    peak_memory_mb: float,
    retraining_memory_mb: float | None = None,
) -> dict[str, float]:
    """Training / unlearning efficiency and speedup.

    Metrics
    -------
    training_time_s      – time to train the initial model
    unlearning_time_s    – time to perform unlearning
    speedup_vs_retrain   – retraining_time / unlearning_time (>1 means faster)
    memory_usage_mb      – peak memory during unlearning
    memory_ratio         – memory_usage / retraining_memory  (≤1 means leaner)
    """
    speedup = retraining_time_s / max(unlearning_time_s, 1e-12)
    mem_ratio = peak_memory_mb / max(retraining_memory_mb, 1e-12) if retraining_memory_mb and retraining_memory_mb > 0 else 1.0

    return {
        "training_time_s": float(training_time_s),
        "unlearning_time_s": float(unlearning_time_s),
        "retraining_time_s": float(retraining_time_s),
        "speedup_vs_retrain": float(speedup),
        "memory_usage_mb": float(peak_memory_mb),
        "retraining_memory_mb": float(retraining_memory_mb) if retraining_memory_mb else 0.0,
        "memory_ratio": float(mem_ratio),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 6. Trust score (composite)
# ═══════════════════════════════════════════════════════════════════════════


def compute_trust_score(
    forget_drop: float,
    max_forget_drop: float = 1.0,
    knowledge_retention: float = 1.0,
    privacy_leakage_score: float = 0.5,
    speedup_vs_retrain: float = 1.0,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Weighted composite trust score.

    Default weights emphasise utility and privacy equally.
    All sub-scores are normalised to [0, 1] before weighting.

    Returns
    -------
    dict with ``trust_score`` and per-component normalised scores.
    """
    if weights is None:
        weights = {
            "forget_quality": 0.30,
            "utility_retention": 0.35,
            "privacy_reduction": 0.25,
            "efficiency": 0.10,
        }

    norm_forget = float(np.clip(forget_drop / max(max_forget_drop, 1e-12), 0.0, 1.0))
    norm_utility = float(np.clip(knowledge_retention, 0.0, 1.0))
    norm_privacy = float(np.clip(1.0 - privacy_leakage_score, 0.0, 1.0))
    norm_efficiency = float(np.clip(speedup_vs_retrain / max(speedup_vs_retrain + 1.0, 1e-12), 0.0, 1.0))

    trust = (
        weights["forget_quality"] * norm_forget
        + weights["utility_retention"] * norm_utility
        + weights["privacy_reduction"] * norm_privacy
        + weights["efficiency"] * norm_efficiency
    )

    return {
        "trust_score": float(trust),
        "norm_forget_quality": norm_forget,
        "norm_utility_retention": norm_utility,
        "norm_privacy_reduction": norm_privacy,
        "norm_efficiency": norm_efficiency,
        "weights": weights,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 7. Curve helpers
# ═══════════════════════════════════════════════════════════════════════════


def compute_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    num_classes: int | None = None,
) -> dict[str, Any]:
    """Return normalised and raw confusion matrices."""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    if num_classes is None:
        num_classes = int(max(y_true.max(), y_pred.max())) + 1

    raw = _sk_confusion_matrix(y_true, y_pred, labels=list(range(num_classes)))
    row_sums = raw.sum(axis=1, keepdims=True)
    row_sums = np.where(row_sums == 0, 1, row_sums)
    normalised = raw / row_sums

    return {
        "confusion_matrix_raw": raw.tolist(),
        "confusion_matrix_normalised": normalised.tolist(),
        "num_classes": num_classes,
    }


def compute_roc_curve(
    y_true: np.ndarray,
    y_scores: np.ndarray,
) -> dict[str, Any]:
    """Compute ROC curve and AUC.

    Parameters
    ----------
    y_true : binary labels (0 / 1).
    y_scores : continuous decision scores (higher = more likely positive).

    Returns
    -------
    dict with ``fpr``, ``tpr``, ``thresholds``, ``auc``.
    """
    y_true = np.asarray(y_true)
    y_scores = np.asarray(y_scores, dtype=np.float64)

    if len(np.unique(y_true)) < 2:
        return {
            "fpr": [0.0, 1.0],
            "tpr": [0.0, 1.0],
            "thresholds": [np.inf, -np.inf],
            "auc": 0.5,
        }

    fpr, tpr, thresholds = _sk_roc_curve(y_true, y_scores)
    auc = float(roc_auc_score(y_true, y_scores))

    return {
        "fpr": fpr.tolist(),
        "tpr": tpr.tolist(),
        "thresholds": thresholds.tolist(),
        "auc": float(auc),
    }


def compute_pr_curve(
    y_true: np.ndarray,
    y_scores: np.ndarray,
) -> dict[str, Any]:
    """Compute precision-recall curve and AUC (average precision).

    Parameters
    ----------
    y_true : binary labels (0 / 1).
    y_scores : continuous decision scores.

    Returns
    -------
    dict with ``precision``, ``recall``, ``thresholds``, ``auc``.
    """
    y_true = np.asarray(y_true)
    y_scores = np.asarray(y_scores, dtype=np.float64)

    if len(np.unique(y_true)) < 2:
        return {
            "precision": [1.0, 0.0],
            "recall": [0.0, 1.0],
            "thresholds": [np.inf, -np.inf],
            "auc": 0.0,
        }

    from sklearn.metrics import precision_recall_curve as _sk_pr_curve

    precision, recall, thresholds = _sk_pr_curve(y_true, y_scores)
    auc = float(average_precision_score(y_true, y_scores))

    return {
        "precision": precision.tolist(),
        "recall": recall.tolist(),
        "thresholds": thresholds.tolist(),
        "auc": float(auc),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 8. Statistical aggregation & significance
# ═══════════════════════════════════════════════════════════════════════════


def _mean_std_ci(
    values: list[float] | np.ndarray,
    confidence: float = 0.95,
) -> dict[str, float]:
    """Return mean, std, CI lower/upper, and n."""
    arr = np.asarray(values, dtype=np.float64)
    n = len(arr)
    if n == 0:
        return {"mean": 0.0, "std": 0.0, "ci_lower": 0.0, "ci_upper": 0.0, "n": 0}
    mean = float(np.mean(arr))
    if n == 1:
        return {"mean": mean, "std": 0.0, "ci_lower": mean, "ci_upper": mean, "n": 1}
    std = float(np.std(arr, ddof=1))
    se = std / math.sqrt(n)
    z = float(_scipy_stats.norm.ppf(0.5 + confidence / 2))
    return {
        "mean": mean,
        "std": std,
        "ci_lower": float(mean - z * se),
        "ci_upper": float(mean + z * se),
        "n": n,
    }


def aggregate_results(results_list: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate a list of per-run result dicts into mean ± std + CI.

    Every numeric key is aggregated; non-numeric keys are kept from the first
    entry.

    Returns
    -------
    ``{key: {mean, std, ci_lower, ci_upper, n}}`` for each numeric key, plus
    ``"meta"`` containing non-numeric fields.
    """
    if not results_list:
        return {}

    numeric_keys: list[str] = []
    meta: dict[str, Any] = {}
    for k, v in results_list[0].items():
        if isinstance(v, (int, float, np.integer, np.floating)):
            numeric_keys.append(k)
        else:
            meta[k] = v

    aggregated: dict[str, Any] = {"meta": meta}
    for k in numeric_keys:
        vals = []
        for r in results_list:
            v = r.get(k)
            if isinstance(v, (int, float, np.integer, np.floating)):
                vals.append(float(v))
        aggregated[k] = _mean_std_ci(vals)

    return aggregated


def compute_statistical_significance(
    results_a: list[dict[str, float]],
    results_b: list[dict[str, float]],
    alpha: float = 0.05,
) -> dict[str, Any]:
    """Compare two algorithms across runs using paired tests.

    For each numeric metric present in both result lists, computes:
      * **Paired t-test** (two-sided) p-value and significance flag
      * **Welch's t-test** p-value (does not assume equal variance)
      * **Wilcoxon signed-rank** p-value (non-parametric, requires ≥ 6 runs)
      * **Cohen's d** effect size (standardised mean difference)
      * **Mean difference** (A − B)

    Returns
    -------
    ``{metric_name: {t_test_p, welch_p, wilco_p, significant, cohens_d, mean_diff}}``
    """
    if not results_a or not results_b:
        return {"error": "Empty result lists"}

    numeric_keys: list[str] = []
    for k, v in results_a[0].items():
        if isinstance(v, (int, float, np.integer, np.floating)):
            numeric_keys.append(k)

    outcome: dict[str, Any] = {}
    for k in numeric_keys:
        a = np.array([float(r[k]) for r in results_a if k in r and isinstance(r[k], (int, float))], dtype=np.float64)
        b = np.array([float(r[k]) for r in results_b if k in r and isinstance(r[k], (int, float))], dtype=np.float64)

        n = min(len(a), len(b))
        if n < 2:
            outcome[k] = {
                "t_test_p": 1.0,
                "welch_p": 1.0,
                "wilco_p": 1.0,
                "significant": False,
                "cohens_d": 0.0,
                "mean_diff": float(a.mean() - b.mean()) if len(a) > 0 and len(b) > 0 else 0.0,
                "n": n,
            }
            continue

        a = a[:n]
        b = b[:n]
        diff = a - b

        _, t_p = _scipy_stats.ttest_rel(a, b)

        _, welch_p = _scipy_stats.ttest_ind(a, b, equal_var=False)

        if n >= 6:
            try:
                stat_w, wilco_p = _scipy_stats.wilcoxon(diff)
            except ValueError:
                wilco_p = 1.0
        else:
            wilco_p = 1.0

        pooled_std = math.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2.0)
        d = float((a.mean() - b.mean()) / pooled_std) if pooled_std > 1e-12 else 0.0

        outcome[k] = {
            "t_test_p": float(t_p),
            "welch_p": float(welch_p),
            "wilco_p": float(wilco_p),
            "significant": bool(t_p < alpha),
            "cohens_d": float(d),
            "mean_diff": float(a.mean() - b.mean()),
            "effect_size_interpretation": _interpret_effect_size(d),
            "n": n,
        }

    return outcome


def _interpret_effect_size(d: float) -> str:
    """Cohen's d convention."""
    d_abs = abs(d)
    if d_abs < 0.2:
        return "negligible"
    if d_abs < 0.5:
        return "small"
    if d_abs < 0.8:
        return "medium"
    return "large"


# ═══════════════════════════════════════════════════════════════════════════
# 9. High-level MetricsComputer orchestrator
# ═══════════════════════════════════════════════════════════════════════════


class MetricsComputer:
    """Compute *all* evaluation metrics for an unlearning experiment.

    Typical usage::

        mc = MetricsComputer(num_classes=10)

        # 1.  Train, get predictions & losses on train/test/forget/retain splits
        # 2.  Call the individual compute_* methods
        # 3.  Use ``full_report`` for a one-shot comprehensive dict
    """

    def __init__(
        self,
        num_classes: int = 2,
        weights: dict[str, float] | None = None,
    ) -> None:
        self.num_classes = num_classes
        self.trust_weights = weights

    # ------------------------------------------------------------------
    # Convenience: full report
    # ------------------------------------------------------------------

    def full_report(
        self,
        *,
        y_true_test: np.ndarray,
        y_pred_test: np.ndarray,
        y_true_retain: np.ndarray | None = None,
        y_pred_retain: np.ndarray | None = None,
        y_true_forget_before: np.ndarray | None = None,
        y_pred_forget_before: np.ndarray | None = None,
        y_true_forget_after: np.ndarray | None = None,
        y_pred_forget_after: np.ndarray | None = None,
        y_true_train: np.ndarray | None = None,
        y_pred_train: np.ndarray | None = None,
        member_losses: np.ndarray | None = None,
        nonmember_losses: np.ndarray | None = None,
        forget_losses_before: np.ndarray | None = None,
        forget_losses_after: np.ndarray | None = None,
        y_scores_mia: np.ndarray | None = None,
        mia_labels: np.ndarray | None = None,
        training_time_s: float = 0.0,
        unlearning_time_s: float = 0.0,
        retraining_time_s: float = 0.0,
        peak_memory_mb: float = 0.0,
        retraining_memory_mb: float | None = None,
        accuracy_before_test: float | None = None,
        accuracy_before_retain: float | None = None,
    ) -> dict[str, Any]:
        """One-shot computation of every metric family."""
        report: dict[str, Any] = {}

        # --- Classification (test) ---
        report["classification"] = compute_classification_metrics(
            y_true_test, y_pred_test, self.num_classes,
        )

        # --- Classification (retain) ---
        if y_true_retain is not None and y_pred_retain is not None:
            report["classification_retain"] = compute_classification_metrics(
                y_true_retain, y_pred_retain, self.num_classes,
            )

        # --- Confusion matrix ---
        report["confusion_matrix"] = compute_confusion_matrix(
            y_true_test, y_pred_test, self.num_classes,
        )

        # --- Forget quality ---
        if y_true_forget_before is not None and y_true_forget_after is not None:
            acc_forget_before = float(accuracy_score(y_true_forget_before, y_pred_forget_before)) if y_pred_forget_before is not None else 0.0
            acc_forget_after = float(accuracy_score(y_true_forget_after, y_pred_forget_after)) if y_pred_forget_after is not None else 0.0
            report["forget_quality"] = compute_forget_quality(
                acc_forget_before,
                acc_forget_after,
                forget_losses_after if forget_losses_after is not None else np.array([]),
                forget_losses_before if forget_losses_before is not None else np.array([]),
            )

        # --- Utility ---
        acc_test_after = float(accuracy_score(y_true_test, y_pred_test))
        acc_retain_after = float(accuracy_score(y_true_retain, y_pred_retain)) if y_true_retain is not None and y_pred_retain is not None else acc_test_after
        report["utility"] = compute_utility_metrics(
            accuracy_before_test=accuracy_before_test if accuracy_before_test is not None else acc_test_after,
            accuracy_after_test=acc_test_after,
            accuracy_before_retain=accuracy_before_retain if accuracy_before_retain is not None else acc_retain_after,
            accuracy_after_retain=acc_retain_after,
        )

        # --- Privacy ---
        if member_losses is not None and nonmember_losses is not None:
            report["privacy"] = compute_privacy_metrics(
                member_losses, nonmember_losses,
            )

        # --- ROC / PR (binary MIA evaluation) ---
        if y_scores_mia is not None and mia_labels is not None:
            report["roc_curve"] = compute_roc_curve(mia_labels, y_scores_mia)
            report["pr_curve"] = compute_pr_curve(mia_labels, y_scores_mia)

        # --- Overfitting gap ---
        if y_true_train is not None and y_pred_train is not None:
            train_acc = float(accuracy_score(y_true_train, y_pred_train))
            test_acc = float(accuracy_score(y_true_test, y_pred_test))
            report["overfitting_gap"] = float(train_acc - test_acc)

        # --- Efficiency ---
        report["efficiency"] = compute_efficiency_metrics(
            training_time_s=training_time_s,
            unlearning_time_s=unlearning_time_s,
            retraining_time_s=retraining_time_s,
            peak_memory_mb=peak_memory_mb,
            retraining_memory_mb=retraining_memory_mb,
        )

        # --- Trust score ---
        forget_drop = report.get("forget_quality", {}).get("forget_drop", 0.0)
        kr = report.get("utility", {}).get("knowledge_retention", 1.0)
        pl = report.get("privacy", {}).get("privacy_leakage_score", 0.5)
        sp = report.get("efficiency", {}).get("speedup_vs_retrain", 1.0)
        report["trust"] = compute_trust_score(
            forget_drop=forget_drop,
            knowledge_retention=kr,
            privacy_leakage_score=pl,
            speedup_vs_retrain=sp,
            weights=self.trust_weights,
        )

        return report


# ═══════════════════════════════════════════════════════════════════════════
# 10. Convenience: compute losses from estimator probabilities
# ═══════════════════════════════════════════════════════════════════════════


def compute_losses(
    estimator: Any,
    X: Any,
    y: np.ndarray,
) -> np.ndarray:
    """Negative log-likelihood (cross-entropy) loss per sample.

    Works with any estimator that exposes ``predict_proba``.
    """
    proba = estimator.predict_proba(X)
    y = np.asarray(y, dtype=int)
    n = len(y)
    eps = 1e-12
    losses = np.zeros(n, dtype=np.float64)
    for i in range(n):
        p = np.clip(proba[i, y[i]], eps, 1.0 - eps)
        losses[i] = -math.log(p)
    return losses
