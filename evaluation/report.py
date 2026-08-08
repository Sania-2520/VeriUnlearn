"""Publication-ready IEEE-paper-quality benchmark report generator."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from evaluation.config import (
    ExperimentConfig,
    get_git_info,
    get_hardware_info,
    get_package_versions,
)
from evaluation.export import ExperimentResults, ResultsExporter


class PublicationReport:
    """Generate IEEE-paper-quality benchmark reports."""

    def __init__(self, config: ExperimentConfig | None = None) -> None:
        # ``config`` is stored as non-optional: callers that do not pass one get
        # a default. If the caller passed none but ``results.config`` carries a
        # real configuration (loaded from a saved run), ``generate_report``
        # rebuilds it from the results so the report reflects the experiment.
        self._config_passed = config is not None
        self.config = config if config is not None else ExperimentConfig()

    def generate_report(
        self,
        results: ExperimentResults,
        figures: list[str] | None = None,
        output_dir: str | Path = "evaluation/results",
    ) -> str:
        """Generate a complete markdown report. Returns the output file path."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if not self._config_passed and results.config:
            try:
                self.config = ExperimentConfig(**results.config)
            except Exception:
                self.config = ExperimentConfig()

        sections: list[str] = []
        sections.append(self._generate_title(results))
        sections.append(self._generate_abstract(results))
        sections.append(self._generate_setup_section(results))
        sections.append(self._generate_algorithms_section(results))
        sections.append(self._generate_results_section(results))
        if figures:
            sections.append(self._generate_visualizations_section(figures))
        sections.append(self._generate_discussion(results))
        sections.append(self._generate_reproducibility_section(results))
        sections.append(self._generate_appendix(results))

        report_content = "\n\n".join(sections)

        report_path = output_dir / "report.md"
        report_path.write_text(report_content, encoding="utf-8")

        return str(report_path)

    # ------------------------------------------------------------------
    # Title and Abstract
    # ------------------------------------------------------------------

    def _generate_title(self, results: ExperimentResults) -> str:
        algos = ", ".join(results.algorithm_names[:5])
        if len(results.algorithm_names) > 5:
            algos += ", et al."
        datasets_str = ", ".join(results.dataset_names)

        lines = [
            f"# {self.config.experiment_name.replace('_', ' ').title()}",
            "",
            "**VeriUnlearn Benchmark Report**",
            "",
            f"> Algorithms: {algos}  ",
            f"> Datasets: {datasets_str}  ",
            f"> Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        ]
        return "\n".join(lines)

    def _generate_abstract(self, results: ExperimentResults) -> str:
        n_algos = len(results.algorithm_names)
        n_datasets = len(results.dataset_names)
        n_metrics = len(results.metric_names)
        n_runs = results.num_runs
        completed = sum(1 for r in results.runs if r.success)
        forget_ratios = sorted({r.forget_ratio for r in results.runs})

        flat = results.summary_flat()
        best_algo = self._find_best_algorithm(flat, "accuracy") if flat else "N/A"

        fr_str = ", ".join(f"{fr:.0%}" for fr in forget_ratios)

        lines = [
            "## Abstract",
            "",
            (
                f"We present a comprehensive evaluation of {n_algos} data unlearning algorithms "
                f"across {n_datasets} benchmark datasets using {n_metrics} quality metrics. "
                f"Our evaluation framework executes {n_runs} total experimental runs "
                f"({completed} completed) across forget ratios of {fr_str}. "
                f"Each algorithm is assessed on utility retention, forgetting quality, "
                f"model stability, and privacy leakage. "
                f"Among the evaluated algorithms, **{best_algo}** achieves the best overall "
                f"accuracy across all datasets. "
                f"All experiments are fully reproducible with deterministic seeding and "
                f"environment snapshots."
            ),
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Experimental Setup
    # ------------------------------------------------------------------

    def _generate_setup_section(self, results: ExperimentResults) -> str:
        cfg = self.config
        lines = [
            "## 1. Experimental Setup",
            "",
            "### 1.1 Datasets",
            "",
            "| Dataset | Classes | Input Shape | Description |",
            "|---------|---------|-------------|-------------|",
        ]

        for ds in cfg.datasets:
            shape_str = "×".join(str(s) for s in ds.input_shape)
            lines.append(
                f"| {ds.name.upper()} | {ds.num_classes} | {shape_str} | "
                f"{'Image' if len(ds.input_shape) >= 3 else 'Text'} classification |"
            )

        lines.extend([
            "",
            "### 1.2 Model Architecture",
            "",
            f"- **Model**: {cfg.model.name}",
            f"- **Hidden Dimension**: {cfg.model.hidden_dim}",
            f"- **Number of Layers**: {cfg.model.num_layers}",
            f"- **Dropout**: {cfg.model.dropout}",
            f"- **LoRA Rank**: {cfg.model.lora_r}",
            f"- **LoRA Alpha**: {cfg.model.lora_alpha}",
            "",
            "### 1.3 Training Configuration",
            "",
            f"- **Optimizer**: {cfg.training.optimizer}",
            f"- **Scheduler**: {cfg.training.scheduler}",
            f"- **Learning Rate**: {cfg.training.learning_rate}",
            f"- **Weight Decay**: {cfg.training.weight_decay}",
            f"- **Batch Size**: {cfg.training.batch_size}",
            f"- **Epochs**: {cfg.training.num_epochs}",
            f"- **Warmup Steps**: {cfg.training.warmup_steps}",
            f"- **Max Grad Norm**: {cfg.training.max_grad_norm}",
            f"- **Early Stopping Patience**: {cfg.training.early_stopping_patience}",
            "",
            "### 1.4 Unlearning Configuration",
            "",
            f"- **Forget Ratios**: {', '.join(f'{r:.0%}' for r in cfg.unlearning.forget_ratios)}",
            f"- **Number of Runs per Configuration**: {cfg.unlearning.num_runs}",
            f"- **Seed Start**: {cfg.unlearning.seed_start}",
            "",
            "### 1.5 Privacy Evaluation",
            "",
            f"- **MIA Samples**: {cfg.privacy.mia_num_samples}",
            f"- **MIA Threshold Percentile**: {cfg.privacy.mia_threshold_percentile}%",
            f"- **Membership Leakage Bins**: {cfg.privacy.membership_leakage_bins}",
            f"- **Attack Confidence Level**: {cfg.privacy.attack_confidence_level}",
        ])
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Algorithms Compared
    # ------------------------------------------------------------------

    def _generate_algorithms_section(self, results: ExperimentResults) -> str:
        descriptions = {
            "retraining": "Full retraining from scratch. Gold-standard but expensive baseline.",
            "sisa": "Sharded, Isolated, Sliced, and Aggregated training for efficient data removal.",
            "scrub": "Scrubbing: approximates unlearning by perturbing model parameters using influence-based gradients.",
            "influence_functions": "Uses influence functions to estimate and reverse the effect of training points.",
            "fine_tune_forgetting": "Fine-tunes the model on the data remaining after forgetting.",
            "si": "Stochastic Information for forgetting via gradient perturbation.",
            "l2_penalty": "L2 regularization penalty to attenuate influence of forgotten data.",
            "fisher_forgetting": "Uses Fisher information matrix to guide parameter updates for forgetting.",
            "gradient_ascent": "Performs gradient ascent on forgotten samples to maximize loss.",
        }

        lines = [
            "## 2. Algorithms Compared",
            "",
            "| Algorithm | Description |",
            "|-----------|-------------|",
        ]
        for algo in results.algorithm_names:
            desc = descriptions.get(algo, algo.replace("_", " ").title())
            display = ResultsExporter._algo_name_to_latex(algo)
            lines.append(f"| {display} | {desc} |")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    def _generate_results_section(self, results: ExperimentResults) -> str:
        sections = [
            "## 3. Results",
            "",
        ]

        sections.append(self._format_metric_table(results.summary_flat()))

        sections.extend(self._generate_per_dataset_analysis(results))
        sections.extend(self._generate_per_forget_ratio_analysis(results))
        sections.extend(self._generate_significance_analysis(results))

        return "\n".join(sections)

    def _generate_per_dataset_analysis(self, results: ExperimentResults) -> list[str]:
        full_summary = results.summary()
        sections: list[str] = [
            "### 3.1 Per-Dataset Analysis",
            "",
        ]

        for ds in results.dataset_names:
            sections.append(f"#### {ResultsExporter._dataset_name_to_latex(ds)}")
            sections.append("")

            header = "| Algorithm | " + " | ".join(
                ResultsExporter._metric_to_latex(m) for m in results.metric_names
            ) + " |"
            sep = "|---" + "|---" * len(results.metric_names) + "|"
            sections.append(header)
            sections.append(sep)

            for algo in results.algorithm_names:
                frs = sorted(full_summary.get(algo, {}).get(ds, {}).keys())
                for fr_str in frs:
                    cell_stats = full_summary[algo][ds][fr_str]
                    row = f"| {ResultsExporter._algo_name_to_latex(algo)} ({fr_str}) |"
                    for m in results.metric_names:
                        stat = cell_stats.get(m, {"mean": 0.0, "std": 0.0})
                        row += f" {stat['mean']:.4f} ± {stat['std']:.4f} |"
                    sections.append(row)

            sections.append("")

        return sections

    def _generate_per_forget_ratio_analysis(self, results: ExperimentResults) -> list[str]:
        full_summary = results.summary()
        all_ratios = sorted({r.forget_ratio for r in results.runs})

        sections: list[str] = [
            "### 3.2 Per-Forget-Ratio Analysis",
            "",
        ]

        for fr in all_ratios:
            fr_str = str(fr)
            sections.append(f"#### Forget Ratio: {fr:.0%}")
            sections.append("")

            header = "| Algorithm | " + " | ".join(
                ResultsExporter._metric_to_latex(m) for m in results.metric_names
            ) + " |"
            sep = "|---" + "|---" * len(results.metric_names) + "|"
            sections.append(header)
            sections.append(sep)

            for algo in results.algorithm_names:
                row_parts: list[str] = [f"| {ResultsExporter._algo_name_to_latex(algo)} |"]
                for ds in results.dataset_names:
                    ds_stats = full_summary.get(algo, {}).get(ds, {})
                    if fr_str in ds_stats:
                        break
                for m in results.metric_names:
                    values: list[float] = []
                    for ds in results.dataset_names:
                        ds_stats = full_summary.get(algo, {}).get(ds, {})
                        if fr_str in ds_stats and m in ds_stats[fr_str]:
                            values.append(ds_stats[fr_str][m]["mean"])
                    if values:
                        import numpy as np
                        mean_val = float(np.mean(values))
                        std_val = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
                        row_parts.append(f" {mean_val:.4f} ± {std_val:.4f} |")
                    else:
                        row_parts.append(" -- |")
                sections.append("".join(row_parts))

            sections.append("")

        return sections

    def _generate_significance_analysis(self, results: ExperimentResults) -> list[str]:
        sections: list[str] = [
            "### 3.3 Statistical Significance",
            "",
        ]

        algos = results.algorithm_names
        metrics = results.metric_names

        has_multiple_runs = any(
            len(results.get_runs(algorithm=a)) > 1 for a in algos
        )

        if not has_multiple_runs:
            sections.append(
                "Statistical significance testing requires multiple runs per configuration. "
                "Insufficient data for significance analysis."
            )
            return sections

        try:
            from scipy import stats as sp_stats

            p_values: dict[tuple[str, str], dict[str, float]] = {}
            for i, algo_a in enumerate(algos):
                for algo_b in algos[i + 1:]:
                    p_values[(algo_a, algo_b)] = {}
                    runs_a = results.get_runs(algorithm=algo_a)
                    runs_b = results.get_runs(algorithm=algo_b)
                    for m in metrics:
                        vals_a = [r.metrics[m] for r in runs_a if m in r.metrics and r.success]
                        vals_b = [r.metrics[m] for r in runs_b if m in r.metrics and r.success]
                        if len(vals_a) >= 2 and len(vals_b) >= 2:
                            try:
                                _, p_val = sp_stats.wilcoxon(vals_a, vals_b, alternative="two-sided")
                                p_values[(algo_a, algo_b)][m] = float(p_val)
                            except ValueError:
                                p_values[(algo_a, algo_b)][m] = 1.0
                        else:
                            p_values[(algo_a, algo_b)][m] = 1.0

            header = "| A vs B | " + " | ".join(
                ResultsExporter._metric_to_latex(m) for m in metrics
            ) + " |"
            sep = "|---" + "|---" * len(metrics) + "|"
            sections.append(header)
            sections.append(sep)

            for i, algo_a in enumerate(algos):
                for algo_b in algos[i + 1:]:
                    pv = p_values.get((algo_a, algo_b), {})
                    row = (
                        f"| {ResultsExporter._algo_name_to_latex(algo_a)} vs "
                        f"{ResultsExporter._algo_name_to_latex(algo_b)} |"
                    )
                    for m in metrics:
                        p = pv.get(m, float("nan"))
                        if p < 0.001:
                            row += " <.001*** |"
                        elif p < 0.01:
                            row += f" {p:.3f}** |"
                        elif p < 0.05:
                            row += f" {p:.3f}* |"
                        else:
                            row += f" {p:.3f} |"
                    sections.append(row)

            sections.extend([
                "",
                "* p<.05, ** p<.01, *** p<.001 (Wilcoxon signed-rank test)*",
            ])

        except ImportError:
            sections.append(
                "Statistical significance analysis requires `scipy`. "
                "Install it with: `pip install scipy`"
            )

        return sections

    def _format_metric_table(self, flat_summary: dict) -> str:
        """Format the main comparison table as markdown."""
        algos = list(flat_summary.keys())
        if not algos:
            return "*No results available.*"

        all_metrics: list[str] = []
        for algo_metrics in flat_summary.values():
            for m in algo_metrics:
                if m not in all_metrics:
                    all_metrics.append(m)

        best = self._find_best_per_column(flat_summary, all_metrics, algos)

        lines = [
            "### 3.0 Main Comparison Table",
            "",
            "| Algorithm | " + " | ".join(
                ResultsExporter._metric_to_latex(m) for m in all_metrics
            ) + " |",
            "|---" + "|---" * len(all_metrics) + "|",
        ]

        for algo in algos:
            row = f"| {ResultsExporter._algo_name_to_latex(algo)} |"
            for m in all_metrics:
                stats = flat_summary.get(algo, {}).get(m, {"mean": 0.0, "std": 0.0})
                mean = stats["mean"]
                std = stats["std"]
                cell = f"{mean:.4f} ± {std:.4f}"
                if best.get(m) == algo:
                    cell = f"**{cell}**"
                row += f" {cell} |"
            lines.append(row)

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Visualizations
    # ------------------------------------------------------------------

    def _generate_visualizations_section(self, figures: list[str]) -> str:
        lines = [
            "## 4. Visualizations",
            "",
        ]
        for i, fig_path in enumerate(figures, 1):
            fname = os.path.basename(fig_path)
            lines.append(f"![Figure {i}: {fname}]({fig_path})")
            lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Discussion
    # ------------------------------------------------------------------

    def _generate_discussion(self, results: ExperimentResults) -> str:
        flat = results.summary_flat()

        best_accuracy = self._find_best_algorithm(flat, "accuracy") if flat else "N/A"
        best_f1 = self._find_best_algorithm(flat, "f1_macro") if flat else "N/A"
        best_time = self._find_best_algorithm(flat, "processing_time_ms", higher_is_better=False) if flat else "N/A"

        forget_ratios = sorted({r.forget_ratio for r in results.runs})
        fr_range = f"{forget_ratios[0]:.0%} to {forget_ratios[-1]:.0%}" if forget_ratios else "N/A"

        lines = [
            "## 5. Discussion",
            "",
            "### 5.1 Key Findings",
            "",
            f"1. **Best Overall Accuracy**: {ResultsExporter._algo_name_to_latex(best_accuracy)} "
            f"achieves the highest mean accuracy across all evaluated datasets and forget ratios.",
            "",
            f"2. **Best F1 Score**: {ResultsExporter._algo_name_to_latex(best_f1)} demonstrates "
            f"the strongest balanced precision-recall performance.",
            "",
            f"3. **Most Efficient**: {ResultsExporter._algo_name_to_latex(best_time)} has the "
            f"lowest processing time, making it suitable for time-sensitive applications.",
            "",
            "### 5.2 Algorithm Trade-offs",
            "",
            "The results highlight the classic trade-off between unlearning quality and computational cost:",
            "",
        ]

        retraining_runs = results.get_runs(algorithm="retraining")
        if retraining_runs:
            retraining_time = sum(
                r.timing.get("processing_time_ms", 0.0) for r in retraining_runs if r.success
            ) / max(len(retraining_runs), 1)
            lines.append(
                f"- **Retraining** serves as the gold-standard baseline with "
                f"mean processing time of {retraining_time:.1f}ms."
            )

        sisa_runs = results.get_runs(algorithm="sisa")
        if sisa_runs and retraining_runs:
            sisa_time = sum(
                r.timing.get("processing_time_ms", 0.0) for r in sisa_runs if r.success
            ) / max(len(sisa_runs), 1)
            if retraining_time > 0:
                speedup = retraining_time / max(sisa_time, 1.0)
                lines.append(
                    f"- **SISA** achieves approximately {speedup:.1f}x speedup over retraining "
                    f"while maintaining competitive quality."
                )

        lines.extend([
            "",
            "### 5.3 Scalability Analysis",
            "",
            f"The evaluation spans forget ratios from {fr_range}, "
            f"covering both small-scale ({forget_ratios[0]:.0%}) and large-scale "
            f"({forget_ratios[-1]:.0%}) forgetting scenarios.",
            "",
            "### 5.4 Limitations",
            "",
            "- Results may vary across hardware configurations and library versions.",
            "- All experiments use synthetic feature representations for text datasets.",
            "- The evaluation is limited to the algorithms and hyperparameters specified in the configuration.",
            "",
        ])

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Reproducibility
    # ------------------------------------------------------------------

    def _generate_reproducibility_section(self, results: ExperimentResults) -> str:
        hw = get_hardware_info()
        git = get_git_info()
        pkgs = get_package_versions()

        cfg = self.config
        lines = [
            "## 6. Reproducibility",
            "",
            "### 6.1 Environment",
            "",
            f"- **Platform**: {hw.get('platform', 'N/A')}",
            f"- **Processor**: {hw.get('processor', 'N/A')}",
            f"- **Python**: {hw.get('python_version', 'N/A')}",
            f"- **Architecture**: {hw.get('architecture', 'N/A')}",
            "",
            "### 6.2 Software Versions",
            "",
            "| Package | Version |",
            "|---------|---------|",
        ]
        for pkg, ver in pkgs.items():
            if ver != "not installed":
                lines.append(f"| {pkg} | {ver} |")

        lines.extend([
            "",
            "### 6.3 Source Control",
            "",
            f"- **Git Commit**: `{git.get('commit', 'N/A')}`",
            f"- **Branch**: {git.get('branch', 'N/A')}",
            f"- **Working Directory Clean**: {not git.get('dirty', True)}",
            "",
            "### 6.4 Seeding",
            "",
            f"- Global Seed: `{cfg.seeds.global_seed}`",
            f"- NumPy Seed: `{cfg.seeds.numpy_seed}`",
            f"- PyTorch Seed: `{cfg.seeds.torch_seed}`",
            f"- CUDA Seed: `{cfg.seeds.cuda_seed}`",
            f"- PYTHONHASHSEED: `{cfg.seeds.python_hash_seed}`",
            "",
            "### 6.5 Reproduction Instructions",
            "",
            "```bash",
            "git clone <repository_url>",
            "cd VERIUNLEARN",
            "python -m venv .venv",
            "source .venv/bin/activate",
            "pip install -r requirements.txt",
            f"export PYTHONHASHSEED={cfg.seeds.python_hash_seed}",
            "python -m evaluation.run_all --config evaluation/results/config.json",
            "```",
            "",
        ])

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Appendix
    # ------------------------------------------------------------------

    def _generate_appendix(self, results: ExperimentResults) -> str:
        cfg = self.config
        import json
        config_json = json.dumps(cfg.to_dict(), indent=2, default=str)

        lines = [
            "## Appendix",
            "",
            "### A. Full Configuration",
            "",
            "```json",
            config_json,
            "```",
            "",
            "### B. Detailed Results",
            "",
            "All raw results are available in the accompanying `results.json` file.",
            "",
            f"Total runs: {results.num_runs}",
            f"Completed: {sum(1 for r in results.runs if r.success)}",
            f"Failed: {sum(1 for r in results.runs if not r.success)}",
            "",
        ]

        if results.runs:
            lines.extend([
                "### C. Per-Run Summary",
                "",
                "| Run | Algorithm | Dataset | Forget Ratio | Seed | Success |",
                "|-----|-----------|---------|--------------|------|---------|",
            ])
            for run in results.runs[:100]:
                lines.append(
                    f"| {run.run_id} "
                    f"| {ResultsExporter._algo_name_to_latex(run.algorithm)} "
                    f"| {ResultsExporter._dataset_name_to_latex(run.dataset)} "
                    f"| {run.forget_ratio:.2f} "
                    f"| {run.seed} "
                    f"| {'Yes' if run.success else 'No'} |"
                )
            if len(results.runs) > 100:
                lines.append("| ... | ... | ... | ... | ... | ... |")
                lines.append(f"*{len(results.runs) - 100} additional runs omitted.*")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_best_algorithm(
        flat_summary: dict,
        metric: str,
        higher_is_better: bool = True,
    ) -> str:
        """Find the algorithm with the best score for a given metric."""
        best_algo = ""
        best_val: float | None = None

        higher_metrics = {
            "accuracy", "f1_macro", "f1_weighted", "precision_macro",
            "recall_macro", "utility_retained", "forgetting_quality",
            "model_stability",
        }

        use_higher = higher_is_better if higher_is_better is not None else (
            metric in higher_metrics
        )

        for algo, metrics in flat_summary.items():
            val = metrics.get(metric, {}).get("mean", 0.0)
            if use_higher:
                if best_val is None or val > best_val:
                    best_val = val
                    best_algo = algo
            else:
                if best_val is None or val < best_val:
                    best_val = val
                    best_algo = algo

        return best_algo

    @staticmethod
    def _find_best_per_column(
        flat_summary: dict,
        metrics: list[str],
        algos: list[str],
    ) -> dict[str, str]:
        """For each metric, determine which algorithm has the best mean."""
        higher_metrics = {
            "accuracy", "f1_macro", "f1_weighted", "precision_macro",
            "recall_macro", "utility_retained", "forgetting_quality",
            "model_stability",
        }
        best: dict[str, str] = {}
        for m in metrics:
            best_val: float | None = None
            best_algo = ""
            use_higher = m in higher_metrics
            for algo in algos:
                val = flat_summary.get(algo, {}).get(m, {}).get("mean", 0.0)
                if use_higher:
                    if best_val is None or val > best_val:
                        best_val = val
                        best_algo = algo
                else:
                    if best_val is None or val < best_val:
                        best_val = val
                        best_algo = algo
            best[m] = best_algo
        return best
