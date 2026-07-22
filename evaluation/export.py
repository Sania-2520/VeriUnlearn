"""Export utilities for CSV, JSON, and LaTeX benchmark results."""
from __future__ import annotations

import csv
import json
import math
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class RunResult:
    """Result of a single benchmark run."""
    run_id: int
    algorithm: str
    dataset: str
    forget_ratio: float
    seed: int
    metrics: dict[str, float] = field(default_factory=dict)
    timing: dict[str, float] = field(default_factory=dict)
    success: bool = True
    error: str = ""


@dataclass
class ExperimentResults:
    """Complete experiment results across all algorithms, datasets, and runs."""
    config: dict[str, Any] = field(default_factory=dict)
    algorithm_names: list[str] = field(default_factory=list)
    dataset_names: list[str] = field(default_factory=list)
    metric_names: list[str] = field(default_factory=list)
    runs: list[RunResult] = field(default_factory=list)

    @property
    def num_runs(self) -> int:
        return len(self.runs)

    def get_runs(
        self,
        algorithm: str | None = None,
        dataset: str | None = None,
        forget_ratio: float | None = None,
    ) -> list[RunResult]:
        """Filter runs by algorithm, dataset, and/or forget_ratio."""
        results = self.runs
        if algorithm is not None:
            results = [r for r in results if r.algorithm == algorithm]
        if dataset is not None:
            results = [r for r in results if r.dataset == dataset]
        if forget_ratio is not None:
            results = [r for r in results if math.isclose(r.forget_ratio, forget_ratio)]
        return results

    def summary(self) -> dict[str, dict[str, dict[str, dict[str, float]]]]:
        """Aggregate results: summary[algorithm][dataset][forget_ratio][metric] = {mean, std, n}."""
        import numpy as np

        agg: dict[str, dict[str, dict[str, dict[str, float]]]] = {}
        for algo in self.algorithm_names:
            agg[algo] = {}
            for ds in self.dataset_names:
                agg[algo][ds] = {}
                for fr in sorted({r.forget_ratio for r in self.get_runs(algorithm=algo, dataset=ds)}):
                    matching = self.get_runs(algorithm=algo, dataset=ds, forget_ratio=fr)
                    agg[algo][ds][str(fr)] = {}
                    for metric in self.metric_names:
                        values = [r.metrics[metric] for r in matching if metric in r.metrics and r.success]
                        if values:
                            agg[algo][ds][str(fr)][metric] = {
                                "mean": float(np.mean(values)),
                                "std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
                                "n": len(values),
                            }
                        else:
                            agg[algo][ds][str(fr)][metric] = {"mean": 0.0, "std": 0.0, "n": 0}
        return agg

    def summary_flat(self) -> dict[str, dict[str, dict[str, float]]]:
        """Flat summary: summary[algorithm][metric] = {mean, std} across all datasets/ratios."""
        import numpy as np

        agg: dict[str, dict[str, dict[str, float]]] = {}
        for algo in self.algorithm_names:
            agg[algo] = {}
            matching = self.get_runs(algorithm=algo)
            for metric in self.metric_names:
                values = [r.metrics[metric] for r in matching if metric in r.metrics and r.success]
                if values:
                    agg[algo][metric] = {
                        "mean": float(np.mean(values)),
                        "std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
                    }
                else:
                    agg[algo][metric] = {"mean": 0.0, "std": 0.0}
        return agg


class ResultsExporter:
    """Export benchmark results to multiple formats."""

    def __init__(self, results: ExperimentResults) -> None:
        self.results = results
        self._summary: dict | None = None
        self._flat_summary: dict | None = None

    @property
    def summary(self) -> dict:
        if self._summary is None:
            self._summary = self.results.summary()
        return self._summary

    @property
    def flat_summary(self) -> dict:
        if self._flat_summary is None:
            self._flat_summary = self.results.summary_flat()
        return self._flat_summary

    # ------------------------------------------------------------------
    # CSV export
    # ------------------------------------------------------------------

    def export_results_csv(self, path: str | Path) -> str:
        """Main results table: algorithms x metrics (mean ± std)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        flat = self.flat_summary
        metrics = self.results.metric_names

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            header = ["Algorithm"]
            for m in metrics:
                header.extend([f"{m} (mean)", f"{m} (std)"])
            writer.writerow(header)

            for algo in self.results.algorithm_names:
                row = [algo]
                for m in metrics:
                    stats = flat.get(algo, {}).get(m, {"mean": 0.0, "std": 0.0})
                    row.append(f"{stats['mean']:.4f}")
                    row.append(f"{stats['std']:.4f}")
                writer.writerow(row)

        return str(path)

    def export_detailed_csv(self, path: str | Path) -> str:
        """Per-run detailed results."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        metrics = self.results.metric_names

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            header = [
                "Run ID", "Algorithm", "Dataset", "Forget Ratio",
                "Seed", "Success", "Error",
            ]
            for m in metrics:
                header.append(m)
            for t in self._all_timing_keys():
                header.append(f"time_{t}")
            writer.writerow(header)

            for run in self.results.runs:
                row = [
                    run.run_id,
                    run.algorithm,
                    run.dataset,
                    f"{run.forget_ratio:.4f}",
                    run.seed,
                    int(run.success),
                    run.error,
                ]
                for m in metrics:
                    val = run.metrics.get(m, float("nan"))
                    if isinstance(val, float):
                        row.append(f"{val:.4f}")
                    else:
                        row.append(str(val))
                for t in self._all_timing_keys():
                    val = run.timing.get(t, 0.0)
                    row.append(f"{val:.4f}")
                writer.writerow(row)

        return str(path)

    def export_comparison_csv(self, path: str | Path) -> str:
        """Pairwise algorithm comparisons (ratio of means for each metric)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        flat = self.flat_summary
        algos = self.results.algorithm_names
        metrics = self.results.metric_names

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Algorithm A", "Algorithm B", "Metric", "Mean A", "Mean B", "Ratio (A/B)"])

            for i, algo_a in enumerate(algos):
                for algo_b in algos[i + 1:]:
                    for m in metrics:
                        a_mean = flat.get(algo_a, {}).get(m, {}).get("mean", 0.0)
                        b_mean = flat.get(algo_b, {}).get(m, {}).get("mean", 0.0)
                        ratio = a_mean / b_mean if b_mean != 0 else float("inf")
                        writer.writerow([
                            algo_a, algo_b, m,
                            f"{a_mean:.4f}", f"{b_mean:.4f}", f"{ratio:.4f}",
                        ])

        return str(path)

    def _all_timing_keys(self) -> list[str]:
        keys: set[str] = set()
        for run in self.results.runs:
            keys.update(run.timing.keys())
        return sorted(keys)

    # ------------------------------------------------------------------
    # JSON export
    # ------------------------------------------------------------------

    def export_results_json(self, path: str | Path) -> str:
        """Full structured results."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "config": self.results.config,
            "algorithms": self.results.algorithm_names,
            "datasets": self.results.dataset_names,
            "metrics": self.results.metric_names,
            "num_runs": self.results.num_runs,
            "runs": [asdict(r) for r in self.results.runs],
            "summary": self._serialize_numpy(self.summary),
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        return str(path)

    def export_config_json(self, config: Any, path: str | Path) -> str:
        """Experiment configuration."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if hasattr(config, "to_dict"):
            data = config.to_dict()
        elif hasattr(config, "__dict__"):
            data = asdict(config) if hasattr(config, "__dataclass_fields__") else vars(config)
        else:
            data = config

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        return str(path)

    def export_summary_json(self, path: str | Path) -> str:
        """Aggregated summary with statistics."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "algorithms": self.results.algorithm_names,
            "datasets": self.results.dataset_names,
            "metrics": self.results.metric_names,
            "summary": self._serialize_numpy(self.summary),
            "flat_summary": self._serialize_numpy(self.flat_summary),
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        return str(path)

    # ------------------------------------------------------------------
    # LaTeX export
    # ------------------------------------------------------------------

    def export_benchmark_table_latex(self, path: str | Path) -> str:
        """Main comparison table for IEEE paper (algorithms x metrics)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        flat = self.flat_summary
        metrics = self.results.metric_names
        algos = self.results.algorithm_names

        best_per_col = self._find_best_per_column(flat, metrics, algos)

        lines: list[str] = []
        lines.append(r"\begin{table*}[t]")
        lines.append(r"\centering")
        lines.append(r"\caption{Unlearning Algorithm Benchmark Results}")
        lines.append(r"\label{tab:benchmark}")
        lines.append(r"\small")
        lines.append(r"\begin{tabular}{l" + "c" * len(metrics) + "}")
        lines.append(r"\toprule")

        header = "Algorithm"
        for m in metrics:
            header += " & " + self._metric_to_latex(m)
        header += r" \\"
        lines.append(header)
        lines.append(r"\midrule")

        for algo in algos:
            row = self._algo_name_to_latex(algo)
            for m in metrics:
                stats = flat.get(algo, {}).get(m, {"mean": 0.0, "std": 0.0})
                mean = stats["mean"]
                std = stats["std"]
                cell = f"{mean:.4f} $\\pm$ {std:.4f}"
                if best_per_col.get(m) == algo:
                    cell = r"\textbf{" + cell + "}"
                row += " & " + cell
            row += r" \\"
            lines.append(row)

        lines.append(r"\bottomrule")
        lines.append(r"\end{tabular}")
        lines.append(r"\end{table*}")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        return str(path)

    def export_metrics_table_latex(self, path: str | Path) -> str:
        """Detailed metrics table, per dataset."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        full_summary = self.summary
        metrics = self.results.metric_names
        algos = self.results.algorithm_names
        datasets = self.results.dataset_names

        lines: list[str] = []
        lines.append(r"\begin{table*}[t]")
        lines.append(r"\centering")
        lines.append(r"\caption{Per-Dataset Unlearning Results}")
        lines.append(r"\label{tab:per_dataset}")
        lines.append(r"\small")

        for ds in datasets:
            lines.append(r"\vspace{2mm}")
            lines.append(r"\subcaption*{" + self._dataset_name_to_latex(ds) + "}")
            lines.append(r"\begin{tabular}{lc" + "c" * (len(metrics) - 1) + "}")
            lines.append(r"\toprule")

            header = "Algorithm & Forget Ratio"
            for m in metrics[1:]:
                header += " & " + self._metric_to_latex(m)
            header += r" \\"
            lines.append(header)
            lines.append(r"\midrule")

            for algo in algos:
                frs = sorted(full_summary.get(algo, {}).get(ds, {}).keys())
                for fr_str in frs:
                    fr = float(fr_str)
                    cell_stats = full_summary[algo][ds][fr_str]
                    row = self._algo_name_to_latex(algo) + f" & {fr:.2f}"
                    for m in metrics[1:]:
                        stat = cell_stats.get(m, {"mean": 0.0, "std": 0.0})
                        row += f" & {stat['mean']:.4f} $\\pm$ {stat['std']:.4f}"
                    row += r" \\"
                    lines.append(row)

            lines.append(r"\bottomrule")
            lines.append(r"\end{tabular}")

        lines.append(r"\end{table*}")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        return str(path)

    def export_significance_table_latex(
        self,
        p_values: dict[tuple[str, str], dict[str, float]] | None = None,
        path: str | Path = "significance.tex",
    ) -> str:
        """Statistical significance results table.

        Args:
            p_values: mapping of (algo_a, algo_b) -> {metric: p_value}.
                      If None, an empty table skeleton is generated.
            path: output file path.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if p_values is None:
            p_values = {}
        metrics = self.results.metric_names
        algos = self.results.algorithm_names

        lines: list[str] = []
        lines.append(r"\begin{table}[t]")
        lines.append(r"\centering")
        lines.append(r"\caption{Statistical Significance (Wilcoxon signed-rank test)}")
        lines.append(r"\label{tab:significance}")
        lines.append(r"\small")
        lines.append(r"\begin{tabular}{ll" + "c" * len(metrics) + "}")
        lines.append(r"\toprule")

        header = "Algorithm A & Algorithm B"
        for m in metrics:
            header += " & " + self._metric_to_latex(m)
        header += r" \\"
        lines.append(header)
        lines.append(r"\midrule")

        for i, algo_a in enumerate(algos):
            for algo_b in algos[i + 1:]:
                pair_key = (algo_a, algo_b)
                pair_pvals = p_values.get(pair_key, {})
                row = (
                    self._algo_name_to_latex(algo_a)
                    + " & "
                    + self._algo_name_to_latex(algo_b)
                )
                for m in metrics:
                    pv = pair_pvals.get(m, float("nan"))
                    if math.isnan(pv):
                        row += " & --"
                    elif pv < 0.001:
                        row += r" & $< .001^{***}$"
                    elif pv < 0.01:
                        row += f" & ${pv:.3f}^{{**}}$"
                    elif pv < 0.05:
                        row += f" & ${pv:.3f}^{{*}}$"
                    else:
                        row += f" & ${pv:.3f}$"
                row += r" \\"
                lines.append(row)

        lines.append(r"\midrule")
        lines.append(r"\multicolumn{" + str(len(metrics) + 2) + r"}{l}{\footnotesize $^{*} p<.05\quad ^{**} p<.01\quad ^{***} p<.001$}")
        lines.append(r"\bottomrule")
        lines.append(r"\end{tabular}")
        lines.append(r"\end{table}")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        return str(path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_best_per_column(
        self,
        flat: dict,
        metrics: list[str],
        algos: list[str],
    ) -> dict[str, str]:
        """For each metric, determine which algorithm has the best mean."""
        best: dict[str, str] = {}
        higher_is_better = {
            "accuracy", "f1_macro", "f1_weighted", "precision_macro",
            "recall_macro", "utility_retained", "forgetting_quality",
            "model_stability",
        }
        for m in metrics:
            best_val: float | None = None
            best_algo = ""
            for algo in algos:
                mean = flat.get(algo, {}).get(m, {}).get("mean", 0.0)
                if m in higher_is_better:
                    if best_val is None or mean > best_val:
                        best_val = mean
                        best_algo = algo
                else:
                    if best_val is None or mean < best_val:
                        best_val = mean
                        best_algo = algo
            best[m] = best_algo
        return best

    @staticmethod
    def _metric_to_latex(metric: str) -> str:
        mapping = {
            "accuracy": "Accuracy",
            "f1_macro": "F1 (macro)",
            "f1_weighted": "F1 (weighted)",
            "precision_macro": "Prec. (macro)",
            "recall_macro": "Recall (macro)",
            "utility_retained": "Utility Ret.",
            "forgetting_quality": "Forget Qual.",
            "model_stability": "Stability",
            "privacy_leakage": "Privacy Leak",
            "processing_time_ms": "Time (ms)",
        }
        return mapping.get(metric, metric.replace("_", " ").title())

    @staticmethod
    def _algo_name_to_latex(name: str) -> str:
        mapping = {
            "retraining": "Retraining",
            "sisa": "SISA",
            "scrub": "Scrub",
            "influence_functions": "Infl. Func.",
            "fine_tune_forgetting": "Fine-tune",
            "si": "SI",
            "l2_penalty": "$L_2$ Penalty",
            "fisher_forgetting": "Fisher Forgetting",
            "gradient_ascent": "Grad. Ascent",
        }
        return mapping.get(name, name.replace("_", " ").title())

    @staticmethod
    def _dataset_name_to_latex(name: str) -> str:
        mapping = {
            "mnist": "MNIST",
            "cifar10": "CIFAR-10",
            "imdb": "IMDB",
            "ag_news": "AG News",
        }
        return mapping.get(name, name)

    @staticmethod
    def _serialize_numpy(obj: Any) -> Any:
        """Recursively convert numpy types to native Python types for JSON."""
        import numpy as np

        if isinstance(obj, dict):
            return {k: ResultsExporter._serialize_numpy(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [ResultsExporter._serialize_numpy(v) for v in obj]
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj
