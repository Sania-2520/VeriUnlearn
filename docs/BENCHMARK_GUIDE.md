# Benchmark Guide

VeriUnlearn includes a comprehensive benchmarking platform to compare unlearning algorithms across datasets and measure the **utility / privacy / latency** trade-off objectively. The platform spans both the production ML Engine (for registered algorithms) and the standalone evaluation framework (for research-grade comparison).

---

## Benchmarking Architecture

```
┌──────────────────────────────────────────────────────────┐
│                  BENCHMARKING PLATFORM                    │
│                                                          │
│  ┌─────────────────────┐    ┌─────────────────────────┐  │
│  │  ML Engine Benchmarks│    │  Evaluation Framework    │  │
│  │  (Production)        │    │  (Standalone Research)   │  │
│  │                      │    │                          │  │
│  │  7 algorithms        │    │  5 algorithms            │  │
│  │  9 datasets          │    │  4 datasets              │  │
│  │  Real model pipeline │    │  scikit-learn models     │  │
│  │  GPU accelerated     │    │  CPU only                │  │
│  └──────────┬───────────┘    └──────────┬──────────────┘  │
│             │                          │                   │
│             └──────────┬───────────────┘                   │
│                        ▼                                  │
│  ┌────────────────────────────────────────────────────┐   │
│  │          Shared Services                            │   │
│  │  BenchmarkService · LeaderboardService ·            │   │
│  │  ComparisonService · PrivacyAttackService ·         │   │
│  │  MetricsEngine · MetricsTracker · ExportService     │   │
│  └────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

---

## What Gets Measured

The `MetricsEngine` computes the following metrics for each (algorithm, dataset, forget ratio, trial) combination:

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
| MIA attack accuracy | `mia_attack_accuracy` | Membership inference success rate (lower = better) |
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

### Composite

| Metric | Key | Description |
|--------|-----|-------------|
| Trust score | `trust_score` | Weighted composite (forget 30%, utility 35%, privacy 25%, efficiency 10%) |

---

## Datasets

### ML Engine (Production Pipeline)

Nine built-in datasets (synthetic + real-world) are seedable:

| Category | Datasets | Description |
|----------|----------|-------------|
| Synthetic | `sentiment_synthetic`, `toxic_synthetic`, `pii_synthetic` | Generated for controlled testing |
| Real-world | `sst2`, `ag_news`, `tweet_eval`, `enron_spam` (adapters) | Public benchmarks |

### Evaluation Framework (Standalone)

Four datasets with deterministic splits:

| Dataset | Type | Classes | Samples | Download |
|---------|------|---------|---------|----------|
| MNIST | Image (grayscale, 28×28) | 10 | 70,000 | Auto via torchvision |
| CIFAR-10 | Image (color, 32×32) | 10 | 60,000 | Auto via torchvision (~170 MB) |
| IMDB | Text (TF-IDF features) | 2 | 50,000 | Auto via torchtext |
| AG News | Text (TF-IDF features) | 4 | 127,600 | Auto via torchtext |

**Note**: CIFAR-10 download may fail on restricted networks. Pre-download to `evaluation/data/cifar-10-python.tar.gz`, or use `--datasets mnist` to skip it.

---

## Running Benchmarks

### Phase 2 Benchmark (Full Platform)

The Phase 2 benchmark evaluates all unlearning algorithms across the platform's dataset registry:

#### Via Makefile

```bash
# Run the default benchmark suite
make benchmark

# Render latency / utility / MIA charts
make graphs

# Run benchmark + graphs together
make benchmark && make graphs
```

#### Via ML Engine API

```bash
# Run a benchmark
curl -X POST http://localhost:8001/benchmarks/run \
  -H "Content-Type: application/json" \
  -d '{"dataset": "ag_news", "algorithms": ["sisa", "hybrid"], "trials": 3}'

# Get results
curl http://localhost:8001/benchmarks/summary
curl http://localhost:8001/benchmarks/results
curl http://localhost:8001/benchmarks/config
```

#### Via Backend API

```bash
curl -X POST http://localhost:8000/api/v1/benchmarks/run \
  -H "Content-Type: application/json" \
  -d '{"dataset": "sentiment_synthetic", "algorithms": ["sisa", "influence_function", "certified_removal", "hybrid"], "trials": 5}'

# Get leaderboard
curl http://localhost:8000/api/v1/benchmarks/leaderboard

# Export results
curl "http://localhost:8000/api/v1/benchmarks/results?format=csv"
curl "http://localhost:8000/api/v1/benchmarks/results?format=json"
```

#### Via CLI Scripts

```bash
python infra/scripts/run_benchmarks.py --dataset sentiment_synthetic --trials 5
python infra/scripts/generate_graphs.py
```

### Standalone Evaluation Framework

The evaluation framework (`evaluation/`) runs independently of the full platform stack — no Docker, PostgreSQL, or Redis required.

#### Quick smoke test (~30 seconds, no GPU)

```bash
python -m evaluation.test_framework
```

This validates all components: config, datasets, algorithms, metrics, runner, visualization, and export.

#### Quick benchmark (~2 minutes on CPU)

```bash
python -m evaluation.run_all --quick
```

Runs 3 algorithms (retrain, SISA, SCRUB) on MNIST with 2,000 samples, 1 forget ratio, and 1 run.

#### Full benchmark

```bash
python -m evaluation.run_all
```

Runs all 5 algorithms across all 4 datasets with 3 forget ratios and 3 runs each (180 total experiment runs). Takes 30–60 minutes on CPU.

#### CLI Options

| Flag | Description | Default |
|------|-------------|---------|
| `--quick` | Minimal config (MNIST only, 1 run, 2,000 samples) | off |
| `--datasets mnist cifar10 ...` | Select specific datasets | all 4 |
| `--algorithms retrain sisa ...` | Select specific algorithms | all 5 |
| `--forget-ratios 0.05 0.10 0.20` | Forget ratios to test | `0.05, 0.10, 0.20` |
| `--num-runs N` | Runs per (algorithm, dataset, ratio) | 3 |
| `--max-samples N` | Cap dataset size | None (full) |
| `--seed N` | Global random seed | 42 |
| `--output-dir PATH` | Result output root | `evaluation/results` |
| `--no-figures` | Skip figure generation | off |
| `--no-export` | Skip CSV/JSON/LaTeX export | off |
| `--no-report` | Skip markdown report | off |
| `--no-zip` | Skip reproducibility ZIP | off |

#### Examples

```bash
# MNIST + CIFAR-10 only, 5 runs, seed 123
python -m evaluation.run_all --datasets mnist cifar10 --num-runs 5 --seed 123

# Only SISA and Influence Functions
python -m evaluation.run_all --algorithms sisa influence_functions

# Custom forget ratios, skip figures
python -m evaluation.run_all --forget-ratios 0.01 0.10 0.50 --no-figures

# Full run to custom directory
python -m evaluation.run_all --output-dir /data/benchmarks
```

---

## Understanding the Results

### Output Directory Structure

Results are organized into timestamped directories:

```
evaluation/results/veriunlearn_benchmark_<timestamp>/
├── config.json                  # Full experiment configuration
├── results.json                 # Raw results (all runs)
├── runs.json                    # Per-run results array
├── summary.json                 # Aggregated mean/std/CI per algorithm×dataset×ratio
├── reproducibility.zip          # Full reproducibility package
├── exports/
│   ├── results.csv              # Summary table
│   ├── detailed.csv             # Per-run detailed metrics
│   ├── comparison.csv           # Side-by-side comparison
│   └── benchmark_table.tex      # LaTeX tabular output
├── tables/latex/
│   ├── preamble.tex
│   ├── main_results.tex
│   └── privacy_summary.tex
└── figures/graphs/
    ├── accuracy_comparison.png/pdf
    ├── latency_comparison.png/pdf
    ├── f1_heatmap.png/pdf
    ├── mia_effectiveness.png/pdf
    ├── privacy_utility_tradeoff.png/pdf
    ├── roc_curves_<dataset>.png/pdf
    └── confusion_matrix_<dataset>_<algorithm>.png/pdf
```

### Interpreting Key Metrics

| Metric | Good Value | Bad Value | Notes |
|--------|-----------|-----------|-------|
| `utility_retained` | > 0.90 | < 0.80 | Closer to 1.0 = better unlearning preserves model quality |
| `mia_accuracy` | < 0.15 | > 0.30 | Lower = attacker can't distinguish deleted vs retained data |
| `forget_drop` | > 0.20 | < 0.05 | Higher = more complete forgetting |
| `speedup_vs_retrain` | > 3.0 | < 1.0 | Higher = faster than full retraining |
| `trust_score` | > 0.90 | < 0.70 | Weighted composite of all metrics |

### Trade-off Interpretation

The fundamental unlearning trade-off is **utility vs. privacy**:
- **SISA**: Best utility retention, moderate privacy, moderate speed
- **Certified Removal**: Strongest privacy guarantee (ε-DP), slightly lower utility
- **Influence Functions**: Fastest latency, good utility, weaker formal guarantees
- **Hybrid**: Balanced across all dimensions

---

## Adding New Algorithms

### To the Evaluation Framework (Standalone)

1. **Create a class** in `evaluation/algorithms.py` implementing the `UnlearningAlgorithm` interface:

```python
class MyAlgorithm(UnlearningAlgorithm):
    def fit(self, dataset, seed=42) -> TrainResult:
        # Train your model
        pass

    def unlearn(self, train_result, forget_idx, retain_idx, dataset, seed=42) -> UnlearnResult:
        # Perform unlearning
        pass

    def evaluate(self, result, dataset) -> dict[str, float]:
        # Return metrics dict
        pass

    def get_params(self) -> dict[str, Any]:
        return {"name": "my_algorithm", "version": "1.0"}
```

2. **Register** in the `get_algorithm()` factory function and `list_algorithms()`
3. **Add default** to `UnlearningConfig.algorithms` tuple in `config.py`
4. **Update CLI choices** in `run_all.py` (`--algorithms` parser)
5. **Validate**: `python -m evaluation.test_framework`

### To the ML Engine (Production)

1. Create module in `packages/ml-engine/unlearning/`
2. Implement the `UnlearningStrategy` ABC (`name`, `execute()`, `estimate_cost()`, `can_handle()`)
3. Register via `AlgorithmRegistry.register(strategy)`
4. Add under `api.py` in the `/unlearn` endpoint handler
5. Add tests in `packages/ml-engine/tests/`

---

## Adding New Datasets

### To the Evaluation Framework

1. **Create a loader** in `evaluation/datasets.py` that returns a `DatasetBundle`:
```python
@register_dataset("my_dataset")
def load_my_dataset(data_dir: str, max_samples: Optional[int] = None) -> DatasetBundle:
    # Return DatasetBundle(X_train, y_train, X_test, y_test, class_names)
    pass
```

2. **Add a `DatasetConfig`** entry with `name`, `num_classes`, and `input_shape`
3. **Register** in `load_by_name()` and CLI choices in `run_all.py`
4. **Validate**: `python -m evaluation.test_framework`

### To the ML Engine

1. Upload via `POST /api/v1/datasets` (multipart form data with schema definition)
2. The system automatically chunks, embeds, and registers the dataset with versioning
3. Register via `POST /api/v1/registry/datasets`

---

## Leaderboards & Comparison

### Viewing Leaderboards

```bash
# Algorithm ranking across benchmarks
curl http://localhost:8000/api/v1/benchmarks/leaderboard
```

### Cross-Algorithm Comparison

`ComparisonService` produces side-by-side analysis:

```bash
# Get comparison report
curl http://localhost:8000/api/v1/benchmarks/comparison?algorithms=sisa,influence,hybrid
```

### Publication-Ready Reports

```bash
# Generate IEEE-style markdown report
python -m evaluation.run_all --no-figures  # Run first, then:
# Report is auto-generated in the output directory
```

---

## Comparison with Published Results

### Reference Results (Synthetic Dataset, 5 trials)

| Algorithm | Utility Retained | MIA Accuracy | Latency (ms) |
|-----------|------------------|--------------|--------------|
| SISA | 0.95 ± 0.02 | 0.12 ± 0.03 | 1250 ± 200 |
| Influence | 0.93 ± 0.03 | 0.15 ± 0.04 | 350 ± 50 |
| Certified Removal | 0.91 ± 0.04 | 0.08 ± 0.02 | 180 ± 30 |
| Hybrid | 0.94 ± 0.02 | 0.11 ± 0.03 | 420 ± 80 |

### Reference Results (Real MNIST Data, forget ratio 0.10, 3 runs)

| Algorithm | Accuracy Before | Accuracy After | Accuracy Drop | Train Time (s) | Unlearn Time (s) |
|-----------|----------------|----------------|---------------|----------------|------------------|
| Retrain | 0.823 | 0.827 | -0.003 | 0.36 | 0.30 |
| SISA | 0.633 | 0.587 | 0.047 | 0.75 | 0.11 |
| SCRUB | 0.823 | 0.780 | 0.043 | 0.54 | 13.86 |
| Influence Functions | 0.823 | 0.837 | -0.013 | 0.34 | 0.73 |
| Fine-Tune Forgetting | 0.823 | 0.737 | 0.087 | 0.34 | 0.86 |

### Interpreting Differences from Published Literature

- **SISA** results depend on shard count — more shards = faster unlearning but lower base accuracy
- **Influence Functions** results depend on Hessian approximation quality (damping, iterations)
- **SCRUB** hyperparameters (distillation temperature, number of epochs) significantly affect runtime
- All results include `BASE_MODEL_NAME` and `DEVICE` in the reproducibility package for exact comparison

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

### Reproducibility Package

Every benchmark run generates a reproducibility ZIP containing:

1. **Config fingerprint** — SHA-256 hash of full `ExperimentConfig`
2. **Hardware snapshot** — Platform, CPU, GPU, Python/library versions
3. **Git info** — Commit hash, branch, dirty status
4. **Package versions** — torch, numpy, scipy, sklearn, etc.
5. **Timestamp** — UTC ISO-8601

### Deterministic Execution

- All dataset splits use seeded `random.Random` instances (not global state)
- Subsampling is deterministic per seed
- Algorithm training uses the applied seed configuration
- `torch.backends.cudnn.deterministic = True` and `benchmark = False` for GPU determinism

---

## Known Limitations

- Benchmark numbers depend on the base model (`BASE_MODEL_NAME`, default `Qwen/Qwen2.5-1.5B-Instruct`) and hardware (CUDA vs CPU — `DEVICE`)
- Latency figures include queue wait under Celery; for pure compute, run the ML Engine single-threaded
- Real-world datasets require network access to HuggingFace unless cached
- CIFAR-10 download (~170 MB) may fail on restricted networks (use `--datasets mnist` as fallback)
- SCRUB is ~10–15× slower than other algorithms due to iterative soft-target distillation
- Text datasets (IMDB, AG News) use TF-IDF features for scikit-learn models in the evaluation framework (not full transformer inference)
- Memory usage may be high for large datasets with many shards (SISA) or gradient computation (Influence Functions)

---

## Related Documents

- [Architecture Guide](ARCHITECTURE_GUIDE.md) — System architecture and data flow
- [Machine Unlearning Guide](machine-unlearning-guide.md) — Algorithm descriptions
- [Verification Guide](verification-guide.md) — Cryptographic proof evaluation
- [Evaluation README](../evaluation/README.md) — Detailed framework documentation
- [FAQ](FAQ.md) — Frequently asked benchmark questions
