#!/usr/bin/env python3
"""Unit tests for evaluation.metrics — trust, privacy, utility, and edge cases."""
from __future__ import annotations

import math

import numpy as np
import pytest


# ── helpers ────────────────────────────────────────────────────────────────
from evaluation.metrics import (
    compute_classification_metrics,
    compute_confusion_matrix,
    compute_efficiency_metrics,
    compute_forget_quality,
    compute_pr_curve,
    compute_privacy_metrics,
    compute_roc_curve,
    compute_statistical_significance,
    compute_trust_score,
    compute_utility_metrics,
    aggregate_results,
    MetricsComputer,
)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Trust score
# ═══════════════════════════════════════════════════════════════════════════


class TestTrustScore:
    """Tests for compute_trust_score."""

    def test_returns_expected_keys(self):
        result = compute_trust_score(
            forget_drop=0.5, knowledge_retention=0.9,
            privacy_leakage_score=0.3, speedup_vs_retrain=2.0,
        )
        for key in (
            "trust_score", "norm_forget_quality", "norm_utility_retention",
            "norm_privacy_reduction", "norm_efficiency", "weights",
        ):
            assert key in result, f"Missing key: {key}"

    def test_known_values(self):
        result = compute_trust_score(
            forget_drop=0.8,
            max_forget_drop=1.0,
            knowledge_retention=0.95,
            privacy_leakage_score=0.7,
            speedup_vs_retrain=0.6,
        )
        # norm components
        assert result["norm_forget_quality"] == pytest.approx(0.8, abs=1e-9)
        assert result["norm_utility_retention"] == pytest.approx(0.95, abs=1e-9)
        assert result["norm_privacy_reduction"] == pytest.approx(0.3, abs=1e-9)
        assert result["norm_efficiency"] == pytest.approx(0.6 / 1.6, abs=1e-9)

        # composite: 0.30*0.8 + 0.35*0.95 + 0.25*0.3 + 0.10*0.375
        expected = 0.30 * 0.8 + 0.35 * 0.95 + 0.25 * 0.3 + 0.10 * (0.6 / 1.6)
        assert result["trust_score"] == pytest.approx(expected, abs=1e-9)

    def test_perfect_scores(self):
        result = compute_trust_score(
            forget_drop=1.0, max_forget_drop=1.0,
            knowledge_retention=1.0, privacy_leakage_score=0.0,
            speedup_vs_retrain=100.0,
        )
        assert result["norm_forget_quality"] == pytest.approx(1.0)
        assert result["norm_utility_retention"] == pytest.approx(1.0)
        assert result["norm_privacy_reduction"] == pytest.approx(1.0)
        assert result["trust_score"] > 0.7

    def test_zero_scores(self):
        result = compute_trust_score(
            forget_drop=0.0, knowledge_retention=0.0,
            privacy_leakage_score=1.0, speedup_vs_retrain=0.0,
        )
        assert result["norm_forget_quality"] == pytest.approx(0.0)
        assert result["norm_utility_retention"] == pytest.approx(0.0)
        assert result["norm_privacy_reduction"] == pytest.approx(0.0)
        assert result["trust_score"] < 0.1

    def test_custom_weights(self):
        weights = {
            "forget_quality": 0.50,
            "utility_retention": 0.50,
            "privacy_reduction": 0.0,
            "efficiency": 0.0,
        }
        result = compute_trust_score(
            forget_drop=1.0, max_forget_drop=1.0,
            knowledge_retention=1.0, privacy_leakage_score=0.5,
            speedup_vs_retrain=1.0, weights=weights,
        )
        assert result["trust_score"] == pytest.approx(1.0)
        assert result["weights"] == weights

    def test_output_in_0_1_range(self):
        result = compute_trust_score(
            forget_drop=0.5, knowledge_retention=0.8,
            privacy_leakage_score=0.4, speedup_vs_retrain=1.5,
        )
        assert 0.0 <= result["trust_score"] <= 1.0

    def test_large_forget_drop_clipped(self):
        result = compute_trust_score(
            forget_drop=5.0, max_forget_drop=1.0,
            knowledge_retention=0.9, privacy_leakage_score=0.2,
            speedup_vs_retrain=2.0,
        )
        assert result["norm_forget_quality"] == pytest.approx(1.0)


# ═══════════════════════════════════════════════════════════════════════════
# 2. Privacy metrics
# ═══════════════════════════════════════════════════════════════════════════


class TestPrivacyMetrics:
    """Tests for compute_privacy_metrics."""

    def test_returns_expected_keys(self):
        result = compute_privacy_metrics(
            member_losses=np.array([0.5, 0.3]),
            nonmember_losses=np.array([1.2, 1.5]),
        )
        for key in (
            "mia_attack_accuracy", "mia_attack_auroc",
            "privacy_leakage_score", "overfitting_gap",
        ):
            assert key in result, f"Missing key: {key}"

    def test_clear_separation_high_auroc(self):
        """Low member losses vs high non-member losses should yield high AUROC."""
        members = np.array([0.1, 0.2, 0.15, 0.12, 0.18])
        nonmembers = np.array([2.0, 3.0, 2.5, 2.8, 3.2])
        result = compute_privacy_metrics(members, nonmembers)
        assert result["mia_attack_auroc"] > 0.9
        assert result["privacy_leakage_score"] < 0.1

    def test_overlapping_distributions(self):
        """Same distribution → AUROC ≈ 0.5, leakage ≈ 0.5."""
        data = np.array([1.0, 1.1, 0.9, 1.05, 0.95])
        result = compute_privacy_metrics(data, data.copy())
        assert result["mia_attack_auroc"] == pytest.approx(0.5, abs=0.05)
        assert result["privacy_leakage_score"] == pytest.approx(0.5, abs=0.05)

    def test_empty_inputs_return_defaults(self):
        result = compute_privacy_metrics(
            member_losses=np.array([]),
            nonmember_losses=np.array([]),
        )
        assert result["mia_attack_accuracy"] == 0.5
        assert result["mia_attack_auroc"] == 0.5
        assert result["privacy_leakage_score"] == 0.5
        assert result["overfitting_gap"] == 0.0

    def test_empty_member_only(self):
        result = compute_privacy_metrics(
            member_losses=np.array([]),
            nonmember_losses=np.array([1.0, 2.0]),
        )
        assert result["mia_attack_accuracy"] == 0.5

    def test_overfitting_gap_positive_when_member_loss_lower(self):
        """If member loss < non-member loss, overfitting_gap should be 0 (clamped)."""
        members = np.array([0.1, 0.2])
        nonmembers = np.array([2.0, 3.0])
        result = compute_privacy_metrics(members, nonmembers)
        assert result["overfitting_gap"] == pytest.approx(0.0)

    def test_overfitting_gap_nonzero_when_member_loss_higher(self):
        """If member loss > non-member loss → positive overfitting gap."""
        members = np.array([5.0, 6.0])
        nonmembers = np.array([0.1, 0.2])
        result = compute_privacy_metrics(members, nonmembers)
        assert result["overfitting_gap"] > 0.0

    def test_mia_accuracy_in_range(self):
        members = np.array([0.5, 0.3, 0.4, 0.6, 0.2])
        nonmembers = np.array([1.0, 1.2, 0.8, 1.1, 0.9])
        result = compute_privacy_metrics(members, nonmembers)
        assert 0.0 <= result["mia_attack_accuracy"] <= 1.0

    def test_single_element_arrays(self):
        result = compute_privacy_metrics(
            member_losses=np.array([0.5]),
            nonmember_losses=np.array([2.0]),
        )
        assert "mia_attack_auroc" in result


# ═══════════════════════════════════════════════════════════════════════════
# 3. Utility metrics
# ═══════════════════════════════════════════════════════════════════════════


class TestUtilityMetrics:
    """Tests for compute_utility_metrics."""

    def test_returns_expected_keys(self):
        result = compute_utility_metrics(
            accuracy_before_test=0.92, accuracy_after_test=0.88,
            accuracy_before_retain=0.93, accuracy_after_retain=0.91,
        )
        for key in (
            "utility_loss", "knowledge_retention",
            "accuracy_test_before", "accuracy_test_after",
            "accuracy_retain_before", "accuracy_retain_after",
        ):
            assert key in result, f"Missing key: {key}"

    def test_known_values(self):
        result = compute_utility_metrics(
            accuracy_before_test=0.92, accuracy_after_test=0.88,
            accuracy_before_retain=0.93, accuracy_after_retain=0.91,
        )
        assert result["utility_loss"] == pytest.approx(0.04, abs=1e-9)
        assert result["knowledge_retention"] == pytest.approx(0.91 / 0.93, abs=1e-9)

    def test_no_degradation(self):
        """When before == after → utility_loss=0, knowledge_retention≈1."""
        result = compute_utility_metrics(
            accuracy_before_test=0.90, accuracy_after_test=0.90,
            accuracy_before_retain=0.91, accuracy_after_retain=0.91,
        )
        assert result["utility_loss"] == pytest.approx(0.0)
        assert result["knowledge_retention"] == pytest.approx(1.0)

    def test_knowledge_retention_capped_at_2(self):
        """Clamped to max 2.0."""
        result = compute_utility_metrics(
            accuracy_before_test=0.90, accuracy_after_test=0.90,
            accuracy_before_retain=0.10, accuracy_after_retain=0.90,
        )
        assert result["knowledge_retention"] <= 2.0

    def test_zero_before_retain(self):
        """Division by near-zero: uses 1e-12 guard."""
        result = compute_utility_metrics(
            accuracy_before_test=0.5, accuracy_after_test=0.5,
            accuracy_before_retain=0.0, accuracy_after_retain=0.5,
        )
        assert math.isfinite(result["knowledge_retention"])

    def test_negative_utility_loss(self):
        """After accuracy > before → negative utility_loss."""
        result = compute_utility_metrics(
            accuracy_before_test=0.80, accuracy_after_test=0.90,
            accuracy_before_retain=0.80, accuracy_after_retain=0.90,
        )
        assert result["utility_loss"] < 0


# ═══════════════════════════════════════════════════════════════════════════
# 4. Forget quality
# ═══════════════════════════════════════════════════════════════════════════


class TestForgetQuality:
    """Tests for compute_forget_quality."""

    def test_returns_expected_keys(self):
        result = compute_forget_quality(
            acc_before_forget=0.92, acc_after_forget=0.50,
            loss_member=np.array([0.5]),
            loss_nonmember=np.array([1.0]),
        )
        for key in (
            "forget_accuracy_before", "forget_accuracy_after",
            "forget_drop", "memorization_score",
        ):
            assert key in result, f"Missing key: {key}"

    def test_known_values(self):
        result = compute_forget_quality(
            acc_before_forget=0.92, acc_after_forget=0.50,
            loss_member=np.array([0.5, 0.3, 0.4]),
            loss_nonmember=np.array([1.2, 1.5, 1.1]),
        )
        assert result["forget_drop"] == pytest.approx(0.42, abs=1e-9)
        expected_mem = np.mean([0.5, 0.3, 0.4]) - np.mean([1.2, 1.5, 1.1])
        assert result["memorization_score"] == pytest.approx(expected_mem, abs=1e-9)

    def test_good_forgetting(self):
        """Large forget drop → effective unlearning."""
        result = compute_forget_quality(
            acc_before_forget=0.95, acc_after_forget=0.10,
            loss_member=np.array([0.1]),
            loss_nonmember=np.array([5.0]),
        )
        assert result["forget_drop"] == pytest.approx(0.85)
        assert result["forget_drop"] > 0.5

    def test_no_forgetting(self):
        """Same accuracy before/after → forget_drop=0."""
        result = compute_forget_quality(
            acc_before_forget=0.90, acc_after_forget=0.90,
            loss_member=np.array([1.0]),
            loss_nonmember=np.array([1.0]),
        )
        assert result["forget_drop"] == pytest.approx(0.0)
        assert result["memorization_score"] == pytest.approx(0.0)

    def test_empty_loss_arrays(self):
        result = compute_forget_quality(
            acc_before_forget=0.8, acc_after_forget=0.4,
            loss_member=np.array([]),
            loss_nonmember=np.array([]),
        )
        assert result["memorization_score"] == pytest.approx(0.0)

    def test_one_sided_empty_losses(self):
        result = compute_forget_quality(
            acc_before_forget=0.8, acc_after_forget=0.4,
            loss_member=np.array([0.5]),
            loss_nonmember=np.array([]),
        )
        assert math.isfinite(result["memorization_score"])


# ═══════════════════════════════════════════════════════════════════════════
# 5. Efficiency metrics
# ═══════════════════════════════════════════════════════════════════════════


class TestEfficiencyMetrics:
    """Tests for compute_efficiency_metrics."""

    def test_returns_expected_keys(self):
        result = compute_efficiency_metrics(
            training_time_s=10.0, unlearning_time_s=5.0,
            retraining_time_s=10.0, peak_memory_mb=128.0,
        )
        for key in (
            "training_time_s", "unlearning_time_s", "retraining_time_s",
            "speedup_vs_retrain", "memory_usage_mb", "memory_ratio",
        ):
            assert key in result, f"Missing key: {key}"

    def test_speedup_calculation(self):
        result = compute_efficiency_metrics(
            training_time_s=10.0, unlearning_time_s=2.0,
            retraining_time_s=10.0, peak_memory_mb=128.0,
        )
        assert result["speedup_vs_retrain"] == pytest.approx(5.0)

    def test_speedup_less_than_one(self):
        """Unlearning slower than retraining."""
        result = compute_efficiency_metrics(
            training_time_s=10.0, unlearning_time_s=20.0,
            retraining_time_s=10.0, peak_memory_mb=64.0,
        )
        assert result["speedup_vs_retrain"] == pytest.approx(0.5)

    def test_memory_ratio(self):
        result = compute_efficiency_metrics(
            training_time_s=10.0, unlearning_time_s=5.0,
            retraining_time_s=10.0, peak_memory_mb=100.0,
            retraining_memory_mb=200.0,
        )
        assert result["memory_ratio"] == pytest.approx(0.5)

    def test_memory_ratio_no_retraining_memory(self):
        result = compute_efficiency_metrics(
            training_time_s=10.0, unlearning_time_s=5.0,
            retraining_time_s=10.0, peak_memory_mb=100.0,
        )
        assert result["memory_ratio"] == pytest.approx(1.0)

    def test_zero_unlearning_time(self):
        result = compute_efficiency_metrics(
            training_time_s=10.0, unlearning_time_s=0.0,
            retraining_time_s=10.0, peak_memory_mb=128.0,
        )
        assert math.isfinite(result["speedup_vs_retrain"])
        assert result["speedup_vs_retrain"] > 1e6


# ═══════════════════════════════════════════════════════════════════════════
# 6. Classification metrics
# ═══════════════════════════════════════════════════════════════════════════


class TestClassificationMetrics:
    """Tests for compute_classification_metrics."""

    def test_perfect_predictions(self):
        y = np.array([0, 1, 2, 0, 1, 2])
        result = compute_classification_metrics(y, y, num_classes=3)
        assert result["accuracy"] == pytest.approx(1.0)
        assert result["f1_macro"] == pytest.approx(1.0)

    def test_known_values_binary(self):
        y_true = np.array([1, 1, 0, 0, 1])
        y_pred = np.array([1, 0, 0, 1, 1])
        result = compute_classification_metrics(y_true, y_pred, num_classes=2)
        assert result["accuracy"] == pytest.approx(0.6)
        assert 0.0 <= result["precision_macro"] <= 1.0
        assert 0.0 <= result["recall_macro"] <= 1.0

    def test_per_class_keys_present(self):
        y = np.array([0, 1, 2, 0, 1])
        result = compute_classification_metrics(y, y, num_classes=3)
        for c in range(3):
            assert f"precision_per_class_{c}" in result
            assert f"recall_per_class_{c}" in result
            assert f"f1_per_class_{c}" in result

    def test_multiclass(self):
        y_true = np.array([0, 1, 2, 2, 0])
        y_pred = np.array([0, 2, 2, 1, 0])
        result = compute_classification_metrics(y_true, y_pred, num_classes=3)
        assert result["accuracy"] == pytest.approx(0.6)

    def test_all_wrong(self):
        y_true = np.array([0, 0, 0])
        y_pred = np.array([1, 1, 1])
        result = compute_classification_metrics(y_true, y_pred, num_classes=2)
        assert result["accuracy"] == pytest.approx(0.0)


# ═══════════════════════════════════════════════════════════════════════════
# 7. ROC / PR curves
# ═══════════════════════════════════════════════════════════════════════════


class TestCurves:
    """Tests for compute_roc_curve and compute_pr_curve."""

    def test_roc_perfect_separation(self):
        y_true = np.array([0, 0, 1, 1])
        y_scores = np.array([0.1, 0.2, 0.9, 0.95])
        result = compute_roc_curve(y_true, y_scores)
        assert result["auc"] == pytest.approx(1.0)

    def test_roc_single_class(self):
        y_true = np.array([0, 0, 0])
        y_scores = np.array([0.1, 0.2, 0.3])
        result = compute_roc_curve(y_true, y_scores)
        assert result["auc"] == pytest.approx(0.5)

    def test_pr_perfect(self):
        y_true = np.array([0, 0, 1, 1])
        y_scores = np.array([0.1, 0.2, 0.9, 0.95])
        result = compute_pr_curve(y_true, y_scores)
        assert result["auc"] > 0.9

    def test_pr_single_class(self):
        y_true = np.array([1, 1, 1])
        y_scores = np.array([0.5, 0.6, 0.7])
        result = compute_pr_curve(y_true, y_scores)
        assert result["auc"] == pytest.approx(0.0)


# ═══════════════════════════════════════════════════════════════════════════
# 8. Confusion matrix
# ═══════════════════════════════════════════════════════════════════════════


class TestConfusionMatrix:
    def test_returns_expected_keys(self):
        y = np.array([0, 1, 1, 0])
        result = compute_confusion_matrix(y, y, num_classes=2)
        assert "confusion_matrix_raw" in result
        assert "confusion_matrix_normalised" in result
        assert "num_classes" in result

    def test_perfect_predictions_diagonal(self):
        y = np.array([0, 1, 0, 1])
        result = compute_confusion_matrix(y, y, num_classes=2)
        raw = result["confusion_matrix_raw"]
        assert raw[0][0] == 2
        assert raw[1][1] == 2
        assert raw[0][1] == 0
        assert raw[1][0] == 0

    def test_normalised_rows_sum_to_one(self):
        y_true = np.array([0, 0, 1, 1, 0, 1])
        y_pred = np.array([0, 1, 1, 0, 0, 1])
        result = compute_confusion_matrix(y_true, y_pred, num_classes=2)
        norm = result["confusion_matrix_normalised"]
        for row in norm:
            assert sum(row) == pytest.approx(1.0, abs=1e-9)


# ═══════════════════════════════════════════════════════════════════════════
# 9. Aggregation & statistical significance
# ═══════════════════════════════════════════════════════════════════════════


class TestAggregateResults:
    def test_empty_list(self):
        assert aggregate_results([]) == {}

    def test_single_run(self):
        results = [{"accuracy": 0.85, "name": "run1"}]
        agg = aggregate_results(results)
        assert agg["accuracy"]["mean"] == pytest.approx(0.85)
        assert agg["accuracy"]["n"] == 1
        assert agg["meta"]["name"] == "run1"

    def test_multiple_runs(self):
        results = [
            {"accuracy": 0.80},
            {"accuracy": 0.90},
            {"accuracy": 0.85},
        ]
        agg = aggregate_results(results)
        assert agg["accuracy"]["mean"] == pytest.approx(0.85)
        assert agg["accuracy"]["n"] == 3
        assert agg["accuracy"]["std"] > 0


class TestStatisticalSignificance:
    def test_identical_distributions(self):
        a = [{"acc": 0.80}, {"acc": 0.82}, {"acc": 0.81}]
        b = [{"acc": 0.80}, {"acc": 0.82}, {"acc": 0.81}]
        result = compute_statistical_significance(a, b)
        assert result["acc"]["significant"] is False
        assert result["acc"]["cohens_d"] == pytest.approx(0.0, abs=1e-9)

    def test_different_distributions(self):
        a = [{"acc": 0.95}, {"acc": 0.96}, {"acc": 0.94}, {"acc": 0.95}, {"acc": 0.97}]
        b = [{"acc": 0.70}, {"acc": 0.72}, {"acc": 0.68}, {"acc": 0.71}, {"acc": 0.69}]
        result = compute_statistical_significance(a, b)
        assert result["acc"]["significant"] is True
        assert result["acc"]["cohens_d"] > 1.0

    def test_empty_inputs(self):
        result = compute_statistical_significance([], [])
        assert "error" in result

    def test_single_run_no_significance(self):
        a = [{"acc": 0.90}]
        b = [{"acc": 0.80}]
        result = compute_statistical_significance(a, b)
        assert result["acc"]["significant"] is False
        assert result["acc"]["n"] == 1


# ═══════════════════════════════════════════════════════════════════════════
# 10. MetricsComputer orchestrator
# ═══════════════════════════════════════════════════════════════════════════


class TestMetricsComputer:
    def test_full_report_keys(self):
        mc = MetricsComputer(num_classes=2)
        report = mc.full_report(
            y_true_test=np.array([0, 1, 1, 0]),
            y_pred_test=np.array([0, 1, 0, 0]),
            accuracy_before_test=0.90,
            accuracy_before_retain=0.91,
            member_losses=np.array([0.3]),
            nonmember_losses=np.array([1.5]),
            training_time_s=10.0,
            unlearning_time_s=3.0,
            retraining_time_s=10.0,
            peak_memory_mb=128.0,
        )
        assert "classification" in report
        assert "utility" in report
        assert "trust" in report
        assert "efficiency" in report
        assert "privacy" in report

    def test_full_report_trust_in_range(self):
        mc = MetricsComputer(num_classes=2)
        report = mc.full_report(
            y_true_test=np.array([0, 1, 1, 0]),
            y_pred_test=np.array([0, 1, 0, 0]),
            accuracy_before_test=0.90,
            accuracy_before_retain=0.91,
            member_losses=np.array([0.3]),
            nonmember_losses=np.array([1.5]),
            training_time_s=10.0,
            unlearning_time_s=3.0,
            retraining_time_s=10.0,
            peak_memory_mb=128.0,
        )
        assert 0.0 <= report["trust"]["trust_score"] <= 1.0
