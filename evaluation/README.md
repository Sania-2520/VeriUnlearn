# VeriUnlearn Evaluation Framework

A self-contained benchmarking suite for comparing machine unlearning algorithms across
datasets, measuring **forget quality**, **utility retention**, **privacy resistance**,
and **efficiency** — all with full reproducibility support.

---

## Overview

The evaluation framework (`evaluation/`) provides everything needed to run, measure, and
report on unlearning algorithm experiments **without requiring the full platform stack**
(Docker, PostgreSQL, Redis, etc.). It depends only on Python 3.12+, NumPy, SciPy,
scikit-learn, PyTorch, and (optionally) matplotlib/seaborn for figure generation.

Key capabilities:

- **5 unlearning algorithms** with a unified `fit → unlearn → evaluate` interface
- **4 built-in datasets** (MNIST, CIFAR-10, IMDB, AG News) with deterministic splits
- **18+ metrics** covering classification quality, forget quality, utility retention,
  privacy leakage, efficiency, and a composite trust score
- **Publication-quality figures** (PDF/PNG) and LaTeX table export
- **Full reproducibility packages** (config fingerprinting, hardware snapshots, seed
  management, deterministic execution)

---

## Directory Structure

```
evaluation/
├── algorithms.py              # 5 unlearning algorithm wrappers
├── config.py                  # ExperimentConfig, SeedConfig, DatasetConfig, …
├── datasets.py                # Dataset loaders, forget-set creation, DataLoaders
├── export.py                  # CSV / JSON / LaTeX export (ResultsExporter)
├── generate_publication_data.py  # Synthetic benchmark data generator
├── metrics.py                 # MetricsComputer + individual metric functions
├── report.py                  # PublicationReport (IEEE-paper-quality markdown)
├── reproducibility.py         # ReproducibilityPackage (ZIP + snapshots)
├── run_all.py                 # CLI entry point (python -m evaluation.run_all)
├── runner.py                  # ExperimentRunner (orchestrates full pipeline)
├── test_framework.py          # End-to-end smoke tests (no GPU required)
├── visualization.py           # PublicationVisualizer (matplotlib/seaborn)
├── tests/
│   ├── test_metrics.py        # Unit tests for metrics module
│   └── test_reproducibility.py # Unit tests for reproducibility module
├── data/                      # Cached dataset files (MNIST/, cifar-10-*)
└── results/                   # Experiment output (timestamped runs)
    ├── real/                  # Real benchmark results
    │   └── mnist_results.json
    ├── publication/           # Publication-ready tables + figures
    │   ├── tables/latex/      # .tex files (main_results, preamble, …)
    │   └── figures/graphs/    # .png + .pdf figures
    └── publication_real/      # Real-data publication output
```

---

## Quick Start

### Smoke test (no GPU, ~30 seconds)

```bash
python -m evaluation.test_framework
```

This validates all components (config, datasets, algorithms, metrics, runner,
visualization, export) without a GPU.

### Quick benchmark (~2 minutes on CPU)

```bash
python -m evaluation.run_all --quick
```

Runs 3 algorithms (retrain, SISA, SCRUB) on MNIST with 2 000 samples, 1 forget
ratio, and 1 run. Outputs results to `evaluation/results/veriunlearn_benchmark_quick_<timestamp>/`.

### Full benchmark

```bash
python -m evaluation.run_all
```

Runs all 5 algorithms across all 4 datasets with 3 forget ratios and 3 runs each
(180 total experiment runs). This takes 30–60 minutes on CPU, longer on GPU.

---

## Running Benchmarks

### CLI Options

| Flag | Description | Default |
|------|-------------|---------|
| `--quick` | Minimal config (MNIST only, 1 run, 2 000 samples) | off |
| `--datasets mnist cifar10 …` | Select specific datasets | all 4 |
| `--algorithms retrain sisa …` | Select specific algorithms | all 5 |
| `--forget-ratios 0.05 0.10 0.20` | Forget ratios to test | `0.05, 0.10, 0.20` |
| `--num-runs N` | Runs per (algorithm, dataset, ratio) | 3 |
| `--max-samples N` | Cap dataset size | None (full) |
| `--seed N` | Global random seed | 42 |
| `--output-dir PATH` | Result output root | `evaluation/results` |
| `--no-figures` | Skip figure generation | off |
| `--no-export` | Skip CSV/JSON/LaTeX export | off |
| `--no-report` | Skip markdown report | off |
| `--no-zip` | Skip reproducibility ZIP | off |

### Examples

```bash
# MNIST + CIFAR-10 only, 5 runs, seed 123
python -m evaluation.run_all --datasets mnist cifar10 --num-runs 5 --seed 123

# Only SISA and Influence Functions
python -m evaluation.run_all --algorithms sisa influence_functions

# Custom forget ratios, skip figures
python -m evaluation.run_all --forget-ratios 0.01 0.10 0.50 --no-figures

# Full run, output to custom directory
python -m evaluation.run_all --output-dir /data/benchmarks
```

### Programmatic API

```python
from evaluation.config import (
    ExperimentConfig, SeedConfig, DatasetConfig,
    ModelConfig, TrainingConfig, UnlearningConfig,
    PrivacyConfig, OutputConfig,
)
from evaluation.runner import ExperimentRunner

config = ExperimentConfig(
    experiment_name="my_experiment",
    seeds=SeedConfig(global_seed=42),
    datasets=(DatasetConfig(name="mnist", max_samples=5000),),
    model=ModelConfig(),
    training=TrainingConfig(batch_size=128, num_epochs=10),
    unlearning=UnlearningConfig(
        algorithms=("retrain", "sisa", "scrub"),
        forget_ratios=(0.10,),
        num_runs=3,
    ),
    privacy=PrivacyConfig(mia_num_samples=500),
    output=OutputConfig(output_dir="my_results"),
)

runner = ExperimentRunner(config)
results = runner.run_all()
```

---

## Algorithms

| # | Algorithm | Class | Guarantee | Best For |
|---|-----------|-------|-----------|----------|
| 1 | **Retrain** | `RetrainAlgorithm` | Gold-standard baseline | Comparison reference |
| 2 | **SISA** | `SISAAlgorithm` | Exact shard removal | Large-scale deletions |
| 3 | **SCRUB** | `SCRUBAlgorithm` | Soft-target distillation | Approximate forgetting |
| 4 | **Influence Functions** | `InfluenceFunctionsAlgorithm` | Gradient-based estimation | Medium-scale, fast |
| 5 | **Fine-Tune Forgetting** | `FineTuneForgettingAlgorithm` | Gradient ascent + fine-tune | Simple approximate |

All algorithms implement the `UnlearningAlgorithm` interface:

```python
class UnlearningAlgorithm(abc.ABC):
    def fit(self, dataset, seed=42) -> TrainResult
    def unlearn(self, train_result, forget_idx, retain_idx, dataset, seed=42) -> UnlearnResult
    def evaluate(self, result, dataset) -> dict[str, float]
    def get_params(self) -> dict[str, Any]
```

### Adding a New Algorithm

1. Create a class inheriting from `UnlearningAlgorithm` in `evaluation/algorithms.py`
2. Implement `fit()`, `unlearn()`, `evaluate()`, and `get_params()`
3. Register it in the `get_algorithm()` factory function and `list_algorithms()`
4. Add the algorithm name to `UnlearningConfig.algorithms` default tuple in `config.py`
5. Update the CLI choices in `run_all.py` (`--algorithms` parser)
6. Run `python -m evaluation.test_framework` to validate

---

## Metrics

### Classification Quality

| Metric | Key | Description |
|--------|-----|-------------|
| Accuracy | `accuracy` | Overall correct predictions |
| Precision (macro) | `precision_macro` | Mean precision across classes |
| Precision (weighted) | `precision_weighted` | Class-weighted precision |
| Recall (macro) | `recall_macro` | Mean recall across classes |
| Recall (weighted) | `recall_weighted` | Class-weighted recall |
| F1 (macro) | `f1_macro` | Harmonic mean of macro precision/recall |
| F1 (weighted) | `f1_weighted` | Class-weighted F1 |
| Per-class P/R/F1 | `precision_per_class_<i>` | Per-class breakdown |

### Forget Quality

| Metric | Key | Description |
|--------|-----|-------------|
| Forget accuracy drop | `forget_drop` | Accuracy before − after on forget set |
| Memorization score | `memorization_score` | Mean member loss − mean non-member loss |

### Utility Retention

| Metric | Key | Description |
|--------|-----|-------------|
| Utility loss | `utility_loss` | Test accuracy drop (lower = better) |
| Knowledge retention | `knowledge_retention` | Retain-set accuracy ratio (closer to 1 = better) |

### Privacy

| Metric | Key | Description |
|--------|-----|-------------|
| MIA attack accuracy | `mia_attack_accuracy` | Membership inference success rate |
| MIA AUROC | `mia_attack_auroc` | Area under ROC for loss-based MIA |
| Privacy leakage score | `privacy_leakage_score` | 1 − AUROC (lower = better) |
| Overfitting gap | `overfitting_gap` | Normalised train−test accuracy gap |

### Efficiency

| Metric | Key | Description |
|--------|-----|-------------|
| Training time | `training_time_s` | Initial model training time |
| Unlearning time | `unlearning_time_s` | Time to perform unlearning |
| Speedup vs retrain | `speedup_vs_retrain` | Retrain time / unlearn time (>1 = faster) |
| Peak memory | `memory_usage_mb` | Peak memory during unlearning |
| Memory ratio | `memory_ratio` | Memory usage relative to retraining |

### Composite

| Metric | Key | Description |
|--------|-----|-------------|
| Trust score | `trust_score` | Weighted composite (forget 30%, utility 35%, privacy 25%, efficiency 10%) |

### Curves and Aggregation

| Function | Description |
|----------|-------------|
| `compute_confusion_matrix()` | Raw + row-normalised confusion matrix |
| `compute_roc_curve()` | FPR, TPR, thresholds, AUC |
| `compute_pr_curve()` | Precision, recall, thresholds, AUC |
| `aggregate_results()` | Mean ± std + 95% CI across runs |
| `compute_statistical_significance()` | Paired t-test, Welch's t-test, Wilcoxon, Cohen's d |
| `compute_losses()` | Per-sample NLL loss from estimator probabilities |

---

## Reproducibility

### Seed Management

The framework applies **5 independent seeds** for full determinism:

| Seed | Scope |
|------|-------|
| `global_seed` | Python `random` module |
| `numpy_seed` | NumPy RNG |
| `torch_seed` | PyTorch CPU RNG |
| `cuda_seed` | PyTorch CUDA RNG |
| `python_hash_seed` | `PYTHONHASHSEED` environment variable |

When `SeedConfig.apply()` is called, it also sets `torch.backends.cudnn.deterministic = True`
and `torch.backends.cudnn.benchmark = False` for GPU determinism.

### Deterministic Execution

- All dataset splits use seeded `random.Random` instances (not global state)
- Subsampling is deterministic per seed
- Algorithm training uses the applied seed configuration

### Reproducibility Packages

Every benchmark run automatically generates:

1. **Config fingerprint** — SHA-256 hash of the full `ExperimentConfig`
2. **Hardware snapshot** — platform, CPU, GPU, Python/library versions
3. **Git info** — commit hash, branch, dirty status
4. **Package versions** — torch, numpy, scipy, sklearn, etc.
5. **Timestamp** — UTC ISO-8601

These are bundled into a reproducibility ZIP via `ReproducibilityPackage`:

```python
from evaluation.reproducibility import ReproducibilityPackage
repro = ReproducibilityPackage()
zip_path = repro.create_reproducibility_zip(results, output_dir)
```

---

## Output Formats

All outputs are written to `evaluation/results/<experiment_name>_<timestamp>/`.

### JSON

| File | Contents |
|------|----------|
| `config.json` | Full `ExperimentConfig` serialisation |
| `results.json` | Raw `ExperimentResults` (all runs) |
| `runs.json` | Per-run results array |
| `summary.json` | Aggregated mean/std/CI per algorithm×dataset×ratio |

### CSV

| File | Contents |
|------|----------|
| `exports/results.csv` | Summary table (algorithm, dataset, ratio, metric → mean±std) |
| `exports/detailed.csv` | Per-run detailed metrics |
| `exports/comparison.csv` | Side-by-side algorithm comparison |

### LaTeX

| File | Contents |
|------|----------|
| `exports/benchmark_table.tex` | `tabular` environment with `\toprule/\midrule/\bottomrule` |
| `exports/metrics_table.tex` | Full metrics table |
| `exports/significance_table.tex` | Statistical significance (p-values, Cohen's d) |
| `tables/latex/preamble.tex` | Shared preamble (`booktabs`, column defs) |
| `tables/latex/main_results.tex` | Main results table |
| `tables/latex/privacy_summary.tex` | Privacy metrics summary |

### Figures (PDF/PNG)

Generated by `PublicationVisualizer.generate_all_figures()`:

| Figure | Description |
|--------|-------------|
| `accuracy_comparison` | Bar chart: accuracy before/after per algorithm |
| `latency_comparison` | Bar chart: training + unlearning time per algorithm |
| `f1_heatmap` | Heatmap: F1 scores across algorithms × datasets |
| `mia_effectiveness` | Bar chart: MIA accuracy before/after unlearning |
| `privacy_utility_tradeoff` | Scatter: privacy leakage vs. utility retention |
| `roc_curves_<dataset>` | ROC curves per algorithm on each dataset |
| `confusion_matrix_<dataset>_<algorithm>` | Confusion matrices per algorithm |

---

## Reference Results

Real benchmark results on MNIST (5 algorithms, forget ratio 0.10, 3 runs):

```json
// evaluation/results/real/mnist_results.json
[
  {
    "algorithm": "retrain", "accuracy_before": 0.8233, "accuracy_after": 0.8267,
    "accuracy_drop": -0.0033, "train_time_s": 0.36, "unlearn_time_s": 0.30
  },
  {
    "algorithm": "sisa", "accuracy_before": 0.6333, "accuracy_after": 0.5867,
    "accuracy_drop": 0.0467, "train_time_s": 0.75, "unlearn_time_s": 0.11
  },
  {
    "algorithm": "scrub", "accuracy_before": 0.8233, "accuracy_after": 0.7800,
    "accuracy_drop": 0.0433, "train_time_s": 0.54, "unlearn_time_s": 13.86
  },
  {
    "algorithm": "influence_functions", "accuracy_before": 0.8233, "accuracy_after": 0.8367,
    "accuracy_drop": -0.0133, "train_time_s": 0.34, "unlearn_time_s": 0.73
  },
  {
    "algorithm": "fine_tune_forgetting", "accuracy_before": 0.8233, "accuracy_after": 0.7367,
    "accuracy_drop": 0.0867, "train_time_s": 0.34, "unlearn_time_s": 0.86
  }
]
```

Summary from the README benchmark table:

| Algorithm | Utility Retained | MIA Accuracy | Latency (ms) |
|---|---|---|---|
| SISA | 0.95 ± 0.02 | 0.12 ± 0.03 | 1250 ± 200 |
| Influence | 0.93 ± 0.03 | 0.15 ± 0.04 | 350 ± 50 |
| Certified Removal | 0.91 ± 0.04 | 0.08 ± 0.02 | 180 ± 30 |
| Hybrid | 0.94 ± 0.02 | 0.11 ± 0.03 | 420 ± 80 |

---

## Tests

```bash
# Smoke tests (no GPU required)
python -m evaluation.test_framework

# Unit tests
pytest evaluation/tests/ -v

# Specific test module
pytest evaluation/tests/test_metrics.py -v
```

The smoke test (`test_framework.py`) validates:

1. **Config** — serialisation, fingerprinting, hardware/git/package info
2. **Datasets** — loading MNIST, CIFAR-10, IMDB, AG News
3. **Algorithms** — fit → unlearn → evaluate for all 5 algorithms
4. **Metrics** — all metric functions with known inputs
5. **Runner** — end-to-end experiment execution
6. **Visualization** — figure generation from mock results
7. **Export** — CSV, JSON, LaTeX output

---

## Known Limitations

- **CIFAR-10 download may fail** on restricted networks (firewall, proxy). The dataset
  is ~170 MB and downloaded via `torchvision.datasets.CIFAR10`. If download fails,
  run benchmarks on MNIST only (`--datasets mnist`) or pre-download to
  `evaluation/data/cifar-10-python.tar.gz`.
- **SCRUB is slow** (~10–15× slower than other algorithms) due to iterative
  soft-target distillation.
- **GPU is not required** but accelerates training for larger datasets. The framework
  falls back to CPU automatically.
- **Text datasets** (IMDB, AG News) use TF-IDF features for scikit-learn models,
  not full transformer inference. For transformer-based evaluation, use the ML Engine
  service directly.
- **Memory usage** may be high for large datasets with many shards (SISA) or
  gradient computation (Influence Functions). Reduce `max_samples` if OOM occurs.
