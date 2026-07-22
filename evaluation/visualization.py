"""Publication-quality visualization generators for VeriUnlearn benchmarks."""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    from matplotlib.gridspec import GridSpec
    from matplotlib.patches import FancyBboxPatch
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    logger.warning("matplotlib not installed — figure generation disabled")

try:
    import seaborn as sns
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False

try:
    from evaluation.runner import ExperimentResults, RunResult
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from evaluation.runner import ExperimentResults, RunResult


# ---------------------------------------------------------------------------
# Style constants
# ---------------------------------------------------------------------------

COLORS = [
    "#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3",
    "#937860", "#DA8BC3", "#8C8C8C", "#CCB974", "#64B5CD",
]
PALETTE = dict(zip([
    "retraining", "sisa", "scrub", "influence_functions", "fine_tune_forgetting",
], COLORS[:5]))

LINE_STYLES = ["-", "--", "-.", ":", (0, (3, 1, 1, 1))]
MARKERS = ["o", "s", "D", "^", "v", "P", "*", "X"]

SINGLE_COL_WIDTH = 3.5
DOUBLE_COL_WIDTH = 7.16
GOLDEN_RATIO = 1.618


def _apply_style() -> None:
    if not HAS_MATPLOTLIB:
        return
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linewidth": 0.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "lines.linewidth": 1.2,
        "lines.markersize": 4,
    })
    try:
        sns.set_palette(COLORS)
    except Exception:
        pass


def _color(algorithm: str) -> str:
    return PALETTE.get(algorithm, COLORS[hash(algorithm) % len(COLORS)])


def _save_figure(fig: plt.Figure, output_path: str) -> str:
    base = Path(output_path)
    base.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png", "svg"):
        fig.savefig(base.with_suffix(f".{ext}"), format=ext)
    plt.close(fig)
    logger.info("Saved figure: %s.{pdf,png,svg}", base)
    return str(base.with_suffix(".pdf"))


def _get_algorithms(results: ExperimentResults) -> list[str]:
    seen: dict[str, None] = {}
    for r in results.runs:
        if r.error is None and r.algorithm not in seen:
            seen[r.algorithm] = None
    return list(seen)


def _get_datasets(results: ExperimentResults) -> list[str]:
    seen: dict[str, None] = {}
    for r in results.runs:
        if r.error is None and r.dataset not in seen:
            seen[r.dataset] = None
    return list(seen)


def _get_forget_ratios(results: ExperimentResults) -> list[float]:
    seen: dict[float, None] = {}
    for r in results.runs:
        if r.error is None and r.forget_ratio not in seen:
            seen[r.forget_ratio] = None
    return sorted(seen)


def _group_by(
    runs: list[RunResult], *keys: str
) -> dict[tuple, list[RunResult]]:
    groups: dict[tuple, list[RunResult]] = {}
    for r in runs:
        if r.error is not None:
            continue
        k = tuple(getattr(r, key) for key in keys)
        groups.setdefault(k, []).append(r)
    return groups


def _mean_std(
    runs: list[RunResult], metric: str
) -> tuple[float, float]:
    vals = [getattr(r, metric) for r in runs if r.error is None]
    if not vals:
        return 0.0, 0.0
    return float(np.mean(vals)), float(np.std(vals))


# ---------------------------------------------------------------------------
# PublicationVisualizer
# ---------------------------------------------------------------------------


class PublicationVisualizer:
    """Generate publication-ready figures."""

    def __init__(self) -> None:
        _apply_style()

    # ------------------------------------------------------------------
    # Master entry point
    # ------------------------------------------------------------------

    def generate_all_figures(
        self, results: ExperimentResults, output_dir: str
    ) -> list[str]:
        if not HAS_MATPLOTLIB:
            logger.error("matplotlib not available — skipping figure generation")
            return []
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        paths: list[str] = []
        paths.append(self.plot_benchmark_heatmap(results.summary, str(out / "benchmark_heatmap")))
        paths.append(self.plot_confusion_matrices(results, str(out / "confusion_matrices")))
        paths.append(self.plot_roc_curves(results, str(out / "roc_curves")))
        paths.append(self.plot_pr_curves(results, str(out / "pr_curves")))
        paths.append(self.plot_radar_chart(results.summary, str(out / "radar_chart")))
        for metric in ("accuracy_after", "f1_after", "forget_accuracy", "trust_score"):
            paths.append(self.plot_metric_bars(results.summary, metric, str(out / f"bars_{metric}")))
        for metric in ("accuracy_after", "trust_score"):
            paths.append(self.plot_forget_ratio_sensitivity(results, metric, str(out / f"sensitivity_{metric}")))
        paths.append(self.plot_privacy_utility_tradeoff(results.summary, str(out / "privacy_utility_tradeoff")))
        paths.append(self.plot_efficiency_comparison(results.summary, str(out / "efficiency_comparison")))
        paths.append(self.plot_run_distributions(results, str(out / "run_distributions")))
        return [p for p in paths if p]

    # ------------------------------------------------------------------
    # 1. Benchmark comparison heatmap
    # ------------------------------------------------------------------

    def plot_benchmark_heatmap(
        self, summary: dict, output_path: str
    ) -> str:
        algo_means = summary.get("algorithm_means", {})
        if not algo_means:
            return ""
        metrics_of_interest = [
            "accuracy_after", "f1_after", "forget_accuracy",
            "mia_success_after", "trust_score", "utility_loss",
            "speedup", "knowledge_retention",
        ]
        algos = list(algo_means.keys())
        metric_labels = [m.replace("_", " ").title() for m in metrics_of_interest]
        data = np.zeros((len(algos), len(metrics_of_interest)))
        for i, algo in enumerate(algos):
            for j, m in enumerate(metrics_of_interest):
                data[i, j] = algo_means[algo].get(m, 0.0)
        row_max = np.max(np.abs(data), axis=1, keepdims=True)
        row_max[row_max == 0] = 1.0
        data_norm = data / row_max
        fig, ax = plt.subplots(figsize=(DOUBLE_COL_WIDTH, max(2.5, len(algos) * 0.5 + 0.8)))
        if HAS_SEABORN:
            sns.heatmap(
                data_norm, ax=ax, annot=data.round(3), fmt="",
                cmap="RdYlGn", vmin=-1, vmax=1,
                xticklabels=metric_labels, yticklabels=[a.replace("_", " ").title() for a in algos],
                linewidths=0.5, linecolor="white",
                cbar_kws={"shrink": 0.8, "label": "Normalised score"},
            )
        else:
            im = ax.imshow(data_norm, cmap="RdYlGn", aspect="auto", vmin=-1, vmax=1)
            ax.set_xticks(range(len(metric_labels)))
            ax.set_xticklabels(metric_labels, rotation=45, ha="right")
            ax.set_yticks(range(len(algos)))
            ax.set_yticklabels([a.replace("_", " ").title() for a in algos])
            plt.colorbar(im, ax=ax, shrink=0.8)
        ax.set_title("Algorithm Comparison — Normalised Metrics", fontweight="bold", pad=10)
        fig.tight_layout()
        return _save_figure(fig, output_path)

    # ------------------------------------------------------------------
    # 2. Confusion matrices (before / after per algorithm)
    # ------------------------------------------------------------------

    def plot_confusion_matrices(
        self, results: ExperimentResults, output_path: str
    ) -> str:
        algorithms = _get_algorithms(results)
        datasets = _get_datasets(results)
        n_algos = len(algorithms)
        n_datasets = len(datasets)
        if n_algos == 0 or n_datasets == 0:
            return ""
        fig, axes = plt.subplots(
            n_datasets, n_algos * 2,
            figsize=(DOUBLE_COL_WIDTH, SINGLE_COL_WIDTH * n_datasets + 0.8),
        )
        if n_datasets == 1:
            axes = np.array([axes])
        if n_algos * 2 == 1:
            axes = axes.reshape(-1, 1)
        for di, ds in enumerate(datasets):
            for ai, algo in enumerate(algorithms):
                runs = [r for r in results.runs if r.dataset == ds and r.algorithm == algo and r.error is None]
                if not runs:
                    for col in (ai * 2, ai * 2 + 1):
                        axes[di, col].set_visible(False)
                    continue
                cm_before = np.mean([np.array(r.confusion_matrix_before, dtype=float) for r in runs], axis=0)
                cm_after = np.mean([np.array(r.confusion_matrix_after, dtype=float) for r in runs], axis=0)
                for col, (cm, tag) in enumerate([(cm_before, "Before"), (cm_after, "After")]):
                    ax = axes[di, ai * 2 + col]
                    cm_pct = cm / (cm.sum(axis=1, keepdims=True) + 1e-10)
                    if HAS_SEABORN:
                        sns.heatmap(cm_pct, ax=ax, cmap="Blues", cbar=False, annot=cm.round(0).astype(int), fmt="", linewidths=0.3, linecolor="white", square=True)
                    else:
                        im = ax.imshow(cm_pct, cmap="Blues", aspect="auto")
                        plt.colorbar(im, ax=ax, fraction=0.046)
                    ax.set_title(f"{algo.replace('_', ' ').title()}\n{tag}", fontsize=7, fontweight="bold")
                    ax.set_xlabel("Predicted", fontsize=6)
                    ax.set_ylabel("True", fontsize=6)
                    ax.tick_params(labelsize=5)
        fig.suptitle("Confusion Matrices — Before vs After Unlearning", fontweight="bold", y=1.01)
        fig.tight_layout()
        return _save_figure(fig, output_path)

    # ------------------------------------------------------------------
    # 3. ROC curves (MIA before/after, all algorithms on one plot)
    # ------------------------------------------------------------------

    def plot_roc_curves(
        self, results: ExperimentResults, output_path: str
    ) -> str:
        datasets = _get_datasets(results)
        algorithms = _get_algorithms(results)
        if not datasets or not algorithms:
            return ""
        n = len(datasets)
        fig, axes = plt.subplots(1, n, figsize=(DOUBLE_COL_WIDTH, SINGLE_COL_WIDTH))
        if n == 1:
            axes = [axes]
        for di, ds in enumerate(datasets):
            ax = axes[di]
            for ai, algo in enumerate(algorithms):
                runs = [r for r in results.runs if r.dataset == ds and r.algorithm == algo and r.error is None]
                if not runs:
                    continue
                c = _color(algo)
                ls = LINE_STYLES[ai % len(LINE_STYLES)]
                for tag, ls_actual, alpha in [("before", "--", 0.4), ("after", "-", 1.0)]:
                    all_fpr: list[np.ndarray] = []
                    all_tpr: list[np.ndarray] = []
                    for r in runs:
                        roc = r.roc_curve_before if tag == "before" else r.roc_curve_after
                        if not roc:
                            continue
                        if "fpr" in roc:
                            all_fpr.append(np.array(roc["fpr"]))
                            all_tpr.append(np.array(roc["tpr"]))
                        else:
                            for key, val in roc.items():
                                if isinstance(val, dict) and "fpr" in val:
                                    all_fpr.append(np.array(val["fpr"]))
                                    all_tpr.append(np.array(val["tpr"]))
                                    break
                    if not all_fpr:
                        continue
                    max_len = max(len(a) for a in all_fpr)
                mean_fpr = np.linspace(0, 1, 200)
                mean_tpr_agg = []
                for ai2, algo in enumerate(algorithms):
                    runs = [r for r in results.runs if r.dataset == ds and r.algorithm == algo and r.error is None]
                    if not runs:
                        continue
                    c = _color(algo)
                    for tag, ls_actual, alpha, lw in [("before", "--", 0.35, 0.8), ("after", "-", 1.0, 1.2)]:
                        tprs = []
                        for r in runs:
                            roc = r.roc_curve_before if tag == "before" else r.roc_curve_after
                            if not roc or "fpr" not in roc:
                                continue
                            fpr_arr = np.array(roc["fpr"])
                            tpr_arr = np.array(roc["tpr"])
                            interp_tpr = np.interp(mean_fpr, fpr_arr, tpr_arr)
                            tprs.append(interp_tpr)
                        if not tprs:
                            continue
                        mean_tpr = np.mean(tprs, axis=0)
                        std_tpr = np.std(tprs, axis=0)
                        label = f"{algo.replace('_', ' ').title()} ({tag})"
                        ax.plot(mean_fpr, mean_tpr, color=c, linestyle=ls_actual, alpha=alpha, linewidth=lw, label=label)
                        ax.fill_between(mean_fpr, np.clip(mean_tpr - std_tpr, 0, 1), np.clip(mean_tpr + std_tpr, 0, 1), color=c, alpha=0.08)
                ax.plot([0, 1], [0, 1], color="grey", linestyle=":", linewidth=0.6, alpha=0.5)
                ax.set_xlabel("False Positive Rate")
                ax.set_ylabel("True Positive Rate")
                ax.set_title(f"MIA ROC — {ds.upper()}", fontweight="bold")
                ax.set_xlim(-0.02, 1.02)
                ax.set_ylim(-0.02, 1.02)
                handles, labels = ax.get_legend_handles_labels()
                if handles:
                    ax.legend(loc="lower right", fontsize=6, framealpha=0.9)
        fig.tight_layout()
        return _save_figure(fig, output_path)

    # ------------------------------------------------------------------
    # 4. Precision-Recall curves
    # ------------------------------------------------------------------

    def plot_pr_curves(
        self, results: ExperimentResults, output_path: str
    ) -> str:
        datasets = _get_datasets(results)
        algorithms = _get_algorithms(results)
        if not datasets or not algorithms:
            return ""
        n = len(datasets)
        fig, axes = plt.subplots(1, n, figsize=(DOUBLE_COL_WIDTH, SINGLE_COL_WIDTH))
        if n == 1:
            axes = [axes]
        for di, ds in enumerate(datasets):
            ax = axes[di]
            mean_recall_grid = np.linspace(0, 1, 200)
            for ai, algo in enumerate(algorithms):
                c = _color(algo)
                for tag, ls_actual, alpha, lw in [("before", "--", 0.35, 0.8), ("after", "-", 1.0, 1.2)]:
                    precs = []
                    runs = [r for r in results.runs if r.dataset == ds and r.algorithm == algo and r.error is None]
                    for r in runs:
                        pr = r.pr_curve_before if tag == "before" else r.pr_curve_after
                        if not pr or "precision" not in pr:
                            if pr:
                                for key, val in pr.items():
                                    if isinstance(val, dict) and "precision" in val:
                                        recall_arr = np.array(val["recall"])
                                        prec_arr = np.array(val["precision"])
                                        interp = np.interp(mean_recall_grid, recall_arr, prec_arr)
                                        precs.append(interp)
                                        break
                            continue
                        recall_arr = np.array(pr["recall"])
                        prec_arr = np.array(pr["precision"])
                        interp = np.interp(mean_recall_grid, recall_arr, prec_arr)
                        precs.append(interp)
                    if not precs:
                        continue
                    mean_p = np.mean(precs, axis=0)
                    std_p = np.std(precs, axis=0)
                    label = f"{algo.replace('_', ' ').title()} ({tag})"
                    ax.plot(mean_recall_grid, mean_p, color=c, linestyle=ls_actual, alpha=alpha, linewidth=lw, label=label)
                    ax.fill_between(mean_recall_grid, np.clip(mean_p - std_p, 0, 1), np.clip(mean_p + std_p, 0, 1), color=c, alpha=0.08)
            ax.set_xlabel("Recall")
            ax.set_ylabel("Precision")
            ax.set_title(f"PR Curve — {ds.upper()}", fontweight="bold")
            ax.set_xlim(-0.02, 1.02)
            ax.set_ylim(-0.02, 1.02)
            handles, labels = ax.get_legend_handles_labels()
            if handles:
                ax.legend(loc="lower left", fontsize=6, framealpha=0.9)
        fig.tight_layout()
        return _save_figure(fig, output_path)

    # ------------------------------------------------------------------
    # 5. Radar chart
    # ------------------------------------------------------------------

    def plot_radar_chart(
        self, summary: dict, output_path: str
    ) -> str:
        algo_means = summary.get("algorithm_means", {})
        if not algo_means:
            return ""
        axes_labels = [
            "Accuracy", "Forget Quality", "Privacy",
            "Efficiency", "Trust", "Retention",
        ]
        axes_keys = [
            "accuracy_after", "forget_accuracy", "mia_success_after",
            "speedup", "trust_score", "knowledge_retention",
        ]
        n_axes = len(axes_labels)
        angles = np.linspace(0, 2 * np.pi, n_axes, endpoint=False).tolist()
        angles += angles[:1]
        fig, ax = plt.subplots(figsize=(SINGLE_COL_WIDTH, SINGLE_COL_WIDTH), subplot_kw=dict(polar=True))
        for ai, (algo, vals) in enumerate(algo_means.items()):
            raw = [vals.get(k, 0.0) for k in axes_keys]
            max_vals = [max(abs(algo_means[a].get(k, 0.0)) for a in algo_means) or 1.0 for k in axes_keys]
            normed = [r / m if m != 0 else 0.0 for r, m in zip(raw, max_vals)]
            normed = [min(max(v, 0.0), 1.0) for v in normed]
            normed += normed[:1]
            c = _color(algo)
            ax.plot(angles, normed, color=c, linewidth=1.2, label=algo.replace("_", " ").title())
            ax.fill(angles, normed, color=c, alpha=0.08)
        ax.set_thetagrids(np.degrees(angles[:-1]), axes_labels, fontsize=8)
        ax.set_ylim(0, 1.1)
        ax.set_title("Algorithm Multi-Axis Comparison", fontweight="bold", pad=18, fontsize=10)
        ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.1), fontsize=7)
        fig.tight_layout()
        return _save_figure(fig, output_path)

    # ------------------------------------------------------------------
    # 6. Grouped bar charts per metric
    # ------------------------------------------------------------------

    def plot_metric_bars(
        self, summary: dict, metric: str, output_path: str
    ) -> str:
        algo_means = summary.get("algorithm_means", {})
        if not algo_means:
            return ""
        algos = list(algo_means.keys())
        means = [algo_means[a].get(f"{metric}_mean", algo_means[a].get(metric, 0.0)) for a in algos]
        stds = [algo_means[a].get(f"{metric}_std", 0.0) for a in algos]
        per_cfg = summary.get("per_config", {})
        datasets_seen: dict[str, None] = {}
        for key in per_cfg:
            parts = key.split("|")
            if len(parts) >= 2:
                datasets_seen[parts[1]] = None
        datasets = list(datasets_seen.keys())
        fig, ax = plt.subplots(figsize=(DOUBLE_COL_WIDTH, SINGLE_COL_WIDTH))
        x = np.arange(len(algos))
        bar_width = 0.8 / max(len(datasets), 1)
        for di, ds in enumerate(datasets):
            ds_means = []
            ds_stds = []
            for algo in algos:
                vals_m = []
                vals_s = []
                for fr_key, stats in per_cfg.items():
                    parts = fr_key.split("|")
                    if len(parts) >= 3 and parts[0] == algo and parts[1] == ds:
                        vals_m.append(stats.get(f"{metric}_mean", stats.get(metric, 0.0)))
                        vals_s.append(stats.get(f"{metric}_std", 0.0))
                ds_means.append(float(np.mean(vals_m)) if vals_m else 0.0)
                ds_stds.append(float(np.mean(vals_s)) if vals_s else 0.0)
            offset = (di - len(datasets) / 2 + 0.5) * bar_width
            color_idx = di % len(COLORS)
            ax.bar(x + offset, ds_means, bar_width * 0.9, yerr=ds_stds, label=ds.upper(),
                   color=COLORS[color_idx], alpha=0.85, capsize=2, error_kw={"linewidth": 0.6})
        ax.set_xticks(x)
        ax.set_xticklabels([a.replace("_", " ").title() for a in algos], rotation=25, ha="right")
        metric_label = metric.replace("_", " ").title()
        ax.set_ylabel(metric_label)
        ax.set_title(f"{metric_label} — By Algorithm", fontweight="bold")
        if datasets:
            ax.legend(fontsize=7)
        fig.tight_layout()
        return _save_figure(fig, output_path)

    # ------------------------------------------------------------------
    # 7. Forget ratio sensitivity (line charts)
    # ------------------------------------------------------------------

    def plot_forget_ratio_sensitivity(
        self, results: ExperimentResults, metric: str, output_path: str
    ) -> str:
        algorithms = _get_algorithms(results)
        datasets = _get_datasets(results)
        if not algorithms or not datasets:
            return ""
        n = len(datasets)
        fig, axes = plt.subplots(1, n, figsize=(DOUBLE_COL_WIDTH, SINGLE_COL_WIDTH))
        if n == 1:
            axes = [axes]
        for di, ds in enumerate(datasets):
            ax = axes[di]
            for ai, algo in enumerate(algorithms):
                groups = _group_by(
                    [r for r in results.runs if r.dataset == ds and r.algorithm == algo and r.error is None],
                    "forget_ratio",
                )
                ratios = sorted(groups.keys())
                if not ratios:
                    continue
                vals = []
                errs = []
                for fr in ratios:
                    m, s = _mean_std(groups[fr], metric)
                    vals.append(m)
                    errs.append(s)
                c = _color(algo)
                ls = LINE_STYLES[ai % len(LINE_STYLES)]
                ax.errorbar(
                    ratios, vals, yerr=errs, color=c, linestyle=ls,
                    marker=MARKERS[ai % len(MARKERS)], capsize=2,
                    linewidth=1.0, markersize=4, label=algo.replace("_", " ").title(),
                )
            ax.set_xlabel("Forget Ratio")
            ax.set_ylabel(metric.replace("_", " ").title())
            ax.set_title(f"Forget Ratio Sensitivity — {ds.upper()}", fontweight="bold")
            ax.legend(fontsize=6)
        fig.tight_layout()
        return _save_figure(fig, output_path)

    # ------------------------------------------------------------------
    # 8. Privacy-utility tradeoff scatter
    # ------------------------------------------------------------------

    def plot_privacy_utility_tradeoff(
        self, summary: dict, output_path: str
    ) -> str:
        algo_means = summary.get("algorithm_means", {})
        if not algo_means:
            return ""
        fig, ax = plt.subplots(figsize=(SINGLE_COL_WIDTH, SINGLE_COL_WIDTH * GOLDEN_RATIO))
        for ai, (algo, vals) in enumerate(algo_means.items()):
            acc = vals.get("accuracy_after", 0.0)
            mia = vals.get("mia_success_after", 0.5)
            c = _color(algo)
            ax.scatter(mia, acc, color=c, s=60, zorder=5, edgecolors="white", linewidths=0.5)
            ax.annotate(
                algo.replace("_", " ").title(),
                (mia, acc), fontsize=6, ha="left", va="bottom",
                xytext=(4, 4), textcoords="offset points",
            )
        ax.set_xlabel("MIA Attack Success (Lower = Better Privacy)")
        ax.set_ylabel("Model Accuracy (Higher = Better Utility)")
        ax.set_title("Privacy–Utility Tradeoff", fontweight="bold")
        ax.set_xlim(-0.02, 1.02)
        fig.tight_layout()
        return _save_figure(fig, output_path)

    # ------------------------------------------------------------------
    # 9. Efficiency comparison
    # ------------------------------------------------------------------

    def plot_efficiency_comparison(
        self, summary: dict, output_path: str
    ) -> str:
        algo_means = summary.get("algorithm_means", {})
        if not algo_means:
            return ""
        algos = list(algo_means.keys())
        times = [algo_means[a].get("unlearning_time_mean", algo_means[a].get("unlearning_time", 0.0)) for a in algos]
        speedups = [algo_means[a].get("speedup_mean", algo_means[a].get("speedup", 1.0)) for a in algos]
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(DOUBLE_COL_WIDTH, SINGLE_COL_WIDTH))
        colors = [_color(a) for a in algos]
        short_names = [a.replace("_", " ").title() for a in algos]
        ax1.barh(short_names, times, color=colors, alpha=0.85, edgecolor="white", linewidth=0.5)
        ax1.set_xlabel("Unlearning Time (s)")
        ax1.set_title("Unlearning Time", fontweight="bold")
        ax2.barh(short_names, speedups, color=colors, alpha=0.85, edgecolor="white", linewidth=0.5)
        ax2.set_xlabel("Speedup vs Retraining")
        ax2.set_title("Speedup Factor", fontweight="bold")
        fig.tight_layout()
        return _save_figure(fig, output_path)

    # ------------------------------------------------------------------
    # 10. Box plots — distribution across runs
    # ------------------------------------------------------------------

    def plot_run_distributions(
        self, results: ExperimentResults, output_path: str
    ) -> str:
        algorithms = _get_algorithms(results)
        if not algorithms:
            return ""
        metrics_to_plot = [
            "accuracy_after", "f1_after", "forget_accuracy",
            "trust_score", "mia_success_after",
        ]
        n_metrics = len(metrics_to_plot)
        fig, axes = plt.subplots(1, n_metrics, figsize=(DOUBLE_COL_WIDTH, SINGLE_COL_WIDTH))
        if n_metrics == 1:
            axes = [axes]
        for mi, metric in enumerate(metrics_to_plot):
            ax = axes[mi]
            data_per_algo = []
            labels = []
            for algo in algorithms:
                vals = [getattr(r, metric) for r in results.runs if r.algorithm == algo and r.error is None]
                data_per_algo.append(vals)
                labels.append(algo.replace("_", " ").title())
            if HAS_SEABORN:
                sns.boxplot(data=data_per_algo, ax=ax, palette=COLORS[:len(algorithms)], width=0.5,
                            fliersize=2, linewidth=0.8)
            else:
                bp = ax.boxplot(data_per_algo, patch_artist=True, widths=0.5)
                for patch, c in zip(bp["boxes"], COLORS[:len(algorithms)]):
                    patch.set_facecolor(c)
                    patch.set_alpha(0.7)
            ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=7)
            ax.set_title(metric.replace("_", " ").title(), fontweight="bold", fontsize=8)
            ax.set_ylabel(metric.replace("_", " ").title(), fontsize=7)
        fig.suptitle("Metric Distributions Across Runs", fontweight="bold", y=1.02)
        fig.tight_layout()
        return _save_figure(fig, output_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    import argparse
    import json

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )
    parser = argparse.ArgumentParser(description="VeriUnlearn Publication Visualizer")
    parser.add_argument("--results-dir", required=True, help="Path to experiment results directory")
    parser.add_argument("--output-dir", default=None, help="Output directory for figures (defaults to results-dir/figures)")
    args = parser.parse_args()
    results_path = Path(args.results_dir)
    if not results_path.exists():
        logger.error("Results directory not found: %s", results_path)
        sys.exit(1)
    runs_path = results_path / "runs.json"
    if not runs_path.exists():
        logger.error("runs.json not found in %s", results_path)
        sys.exit(1)
    runs_data = json.loads(runs_path.read_text())
    runs = []
    valid_fields = set(RunResult.__dataclass_fields__.keys())
    for rd in runs_data:
        filtered = {k: v for k, v in rd.items() if k in valid_fields}
        runs.append(RunResult(**filtered))
    summary_path = results_path / "summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
    config_path = results_path / "config.json"
    if config_path.exists():
        from evaluation.config import ExperimentConfig
        config = ExperimentConfig.load(config_path)
    else:
        config = ExperimentConfig()
    results = ExperimentResults(
        config=config,
        runs=runs,
        summary=summary,
        hardware_info={},
        git_info={},
        package_versions={},
        timestamp="",
    )
    out_dir = args.output_dir or str(results_path / "figures")
    viz = PublicationVisualizer()
    paths = viz.generate_all_figures(results, out_dir)
    print(f"\nGenerated {len(paths)} figure(s) in {out_dir}/")
    for p in paths:
        print(f"  {p}")


if __name__ == "__main__":
    main()
