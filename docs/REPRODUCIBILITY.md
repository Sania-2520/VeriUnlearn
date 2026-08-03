# VeriUnlearn Benchmark Reproducibility

This document lists the **exact commands** required to reproduce every result under
`evaluation/results/`. Two distinct kinds of output exist, and they must not be confused:

- **`publication/`** — synthetic illustrative data produced by
  `evaluation/generate_publication_data.py`. Used for paper figures only; **not** an
  empirical result.
- **`real/`**, **`publication_real/`**, **`phase2_*`** — genuine benchmark runs produced
  by the real framework (`evaluation.run_all`). These are the empirical claims.

---

## 0. Environment

- Python 3.12+
- Dependencies: `numpy`, `scipy`, `scikit-learn`, `torch`, `matplotlib`, `seaborn`
  (figures only). No Docker/Postgres/Redis needed.
- Install from repo root:

```bash
pip install -r packages/ml-engine/requirements.txt
pip install numpy scipy scikit-learn torch matplotlib seaborn
```

Seeding is handled internally by `SeedConfig.apply()` (5 independent RNG seeds +
`PYTHONHASHSEED`, deterministic cuDNN). No global seed flags are needed beyond
`--seed`.

---

## 1. Smoke / Validation

```bash
python -m evaluation.test_framework     # ~30 s, no GPU
pytest evaluation/tests/ -v             # unit tests
```

---

## 2. Quick benchmark (MNIST, CPU, ~2 min)

```bash
python -m evaluation.run_all --quick
```

Produces `evaluation/results/veriunlearn_benchmark_quick_<timestamp>/`.

---

## 3. Full benchmark (all datasets, all algorithms)

```bash
python -m evaluation.run_all
```

Runs 5 algorithms (retraining, sisa, scrub, influence_functions, fine_tune_forgetting)
across 4 datasets (mnist, cifar10, imdb, ag_news) at forget ratios 0.05 / 0.10 / 0.20,
3 runs each (~180 runs, 30–60 min CPU).

Selective variants:

```bash
# Reproduce the MNIST real results exactly (5 algorithms, ratio 0.10, 3 runs)
python -m evaluation.run_all \
  --datasets mnist \
  --algorithms retraining sisa scrub influence_functions fine_tune_forgetting \
  --forget-ratios 0.10 \
  --num-runs 3 \
  --seed 42

# MNIST + CIFAR-10, 5 runs, custom seed
python -m evaluation.run_all --datasets mnist cifar10 --num-runs 5 --seed 123

# Only SISA and Influence Functions
python -m evaluation.run_all --algorithms sisa influence_functions
```

CLI flags (from `run_all.py:43`):

| Flag | Default |
|---|---|
| `--quick` | off |
| `--datasets {mnist,cifar10,imdb,ag_news}` | all 4 |
| `--algorithms {retraining,sisa,scrub,influence_functions,fine_tune_forgetting}` | all 5 |
| `--forget-ratios FLOAT...` | 0.05 0.10 0.20 |
| `--num-runs N` | 3 |
| `--max-samples N` | unlimited |
| `--seed N` | 42 |
| `--output-dir PATH` | `evaluation/results` |
| `--no-figures` / `--no-export` / `--no-report` / `--no-zip` | off |

---

## 4. Publication figures & tables from a results dir

```bash
python -m evaluation.visualization --results-dir evaluation/results/<run> \
  --output-dir evaluation/results/<run>/figures
```

Every run already emits: `config.json`, `results.json`, `runs.json`, `summary.json`,
`exports/*.csv`, `exports/*.tex`, `tables/latex/*.tex`, `figures/graphs/*.{png,pdf}`,
and a reproducibility ZIP (config fingerprint + hardware snapshot + git info).

---

## 5. Synthetic publication data (figures only — not empirical)

```bash
python -m evaluation.generate_publication_data
```

Writes `evaluation/results/publication/summary.json` + `scalability.json`. This is
**illustrative data for layout/papers only** and must not be cited as a benchmark
result. The empirical numbers live in `evaluation/results/real/` and
`publication_real/`.

---

## 6. Known result files

| Path | Content |
|---|---|
| `evaluation/results/real/mnist_results.json` | Real MNIST run (5 algorithms, ratio 0.10, 3 runs) |
| `evaluation/results/publication_real/` | Real-run publication figures + tables + raw results |
| `evaluation/results/publication/` | **Synthetic** generator output (see §5) |
| `evaluation/results/phase2_complete/`, `phase2_validation/` | Prior phase benchmark outputs |
| `evaluation/results/smoke_test/` | `test_framework` output |

## 7. Verification

- Config fingerprint and package versions are embedded in each run's reproducibility
  ZIP — compare fingerprints across machines to confirm identical configurations.
- On restricted networks CIFAR-10 (~170 MB) may fail to download; use
  `--datasets mnist` or pre-stage `evaluation/data/cifar-10-python.tar.gz`.
