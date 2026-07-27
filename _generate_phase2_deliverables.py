"""Generate all Phase 2 deliverables from the complete 300-run benchmark."""
import json, sys, os, logging
sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
logging.basicConfig(level=logging.INFO)

from evaluation.config import ExperimentConfig, DatasetConfig, SeedConfig, ModelConfig, TrainingConfig, UnlearningConfig, PrivacyConfig, OutputConfig
from evaluation.export import ExperimentResults, ResultsExporter, RunResult
from evaluation.visualization import PublicationVisualizer
from evaluation.report import PublicationReport
from evaluation.reproducibility import ReproducibilityPackage

PHASE2_DIR = "evaluation/results/phase2_complete"

# Load runs.json
with open(f"{PHASE2_DIR}/runs.json") as f:
    all_runs_data = json.load(f)

runs_list = all_runs_data if isinstance(all_runs_data, list) else all_runs_data.get("runs", [])

# Determine metric keys from data (everything except metadata fields)
RUN_META = {"algorithm", "dataset", "forget_ratio", "run_id", "seed", "success", "error",
            "confusion_matrix_before", "confusion_matrix_after",
            "roc_curve_before", "roc_curve_after",
            "pr_curve_before", "pr_curve_after", "elapsed_seconds"}
TIMING_KEYS = {"training_time", "unlearning_time", "speedup", "memory_peak_mb"}
METRIC_KEYS = {"accuracy_before", "accuracy_after", "f1_before", "f1_after",
               "precision_before", "recall_before", "precision_after", "recall_after",
               "forget_accuracy", "memorization_score",
               "mia_success_before", "mia_success_after", "privacy_leakage",
               "trust_score", "utility_loss", "knowledge_retention"}

run_results = []
for r in runs_list:
    if not isinstance(r, dict) or "algorithm" not in r:
        continue
    metrics = {k: v for k, v in r.items() if k not in RUN_META and k in METRIC_KEYS}
    timing = {k: v for k, v in r.items() if k in TIMING_KEYS}
    run_results.append(RunResult(
        run_id=r.get("run_id", 0),
        algorithm=r["algorithm"],
        dataset=r["dataset"],
        forget_ratio=r.get("forget_ratio", 0.05),
        seed=r.get("seed", 42),
        metrics=metrics,
        timing=timing,
        success=r.get("success", True),
        error=str(r.get("error", "") or ""),
    ))

print(f"Loaded {len(run_results)} run results")

# Reconstruct config
config = ExperimentConfig(
    experiment_name="veriunlearn_phase2_complete",
    seeds=SeedConfig(global_seed=42),
    datasets=[
        DatasetConfig(name="mnist", num_classes=10, input_shape=(1, 28, 28), mean=(0.1307,), std=(0.3081,), max_samples=500),
        DatasetConfig(name="cifar10", num_classes=10, input_shape=(3, 32, 32), mean=(0.4914, 0.4822, 0.4465), std=(0.2023, 0.1994, 0.2010), max_samples=500),
        DatasetConfig(name="imdb", num_classes=2, vocab_size=30000, max_seq_length=512, input_shape=(512,), max_samples=500),
        DatasetConfig(name="ag_news", num_classes=4, vocab_size=30000, max_seq_length=256, input_shape=(256,), max_samples=500),
    ],
    model=ModelConfig(name="logistic_regression"),
    training=TrainingConfig(),
    unlearning=UnlearningConfig(
        algorithms=("retrain", "sisa", "scrub", "influence_functions", "fine_tune_forgetting"),
        forget_ratios=(0.05, 0.10, 0.25),
        num_runs=5,
        seed_start=42,
    ),
    privacy=PrivacyConfig(),
    output=OutputConfig(output_dir=PHASE2_DIR),
)

# Build ExperimentResults (export module version)
metric_names = sorted(METRIC_KEYS)
results = ExperimentResults(
    config=config.to_dict(),
    algorithm_names=list(config.unlearning.algorithms),
    dataset_names=[d.name for d in config.datasets],
    metric_names=metric_names,
    runs=run_results,
)

# 1. Export CSV, JSON, LaTeX
exporter = ResultsExporter(results)
export_dir = f"{PHASE2_DIR}/exports"
os.makedirs(export_dir, exist_ok=True)

csv_path = exporter.export_results_csv(f"{export_dir}/results.csv")
print(f"CSV: {csv_path}")

detailed_csv = exporter.export_detailed_csv(f"{export_dir}/results_detailed.csv")
print(f"Detailed CSV: {detailed_csv}")

comparison_csv = exporter.export_comparison_csv(f"{export_dir}/comparison.csv")
print(f"Comparison CSV: {comparison_csv}")

json_path = exporter.export_results_json(f"{export_dir}/results.json")
print(f"JSON: {json_path}")

summary_json = exporter.export_summary_json(f"{export_dir}/summary.json")
print(f"Summary JSON: {summary_json}")

latex_bench = exporter.export_benchmark_table_latex(f"{export_dir}/benchmark_table.tex")
print(f"LaTeX (benchmark): {latex_bench}")

latex_metrics = exporter.export_metrics_table_latex(f"{export_dir}/metrics_table.tex")
print(f"LaTeX (metrics): {latex_metrics}")

latex_sig = exporter.export_significance_table_latex(path=f"{export_dir}/significance_table.tex")
print(f"LaTeX (significance): {latex_sig}")

# 2. Generate publication-quality visualizations
figures = []
try:
    viz = PublicationVisualizer()
    figures = viz.generate_all_figures(results, f"{PHASE2_DIR}/figures")
    print(f"Generated {len(figures)} figures")
except Exception as e:
    print(f"Figure generation error: {e}")
    import traceback; traceback.print_exc()

# 3. Generate benchmark report
try:
    report = PublicationReport(config)
    report_path = report.generate_report(results, figures=figures, output_dir=PHASE2_DIR)
    print(f"Report: {report_path}")
except Exception as e:
    print(f"Report generation error: {e}")
    import traceback; traceback.print_exc()

# 4. Generate reproducibility package
try:
    repro = ReproducibilityPackage()
    snap = repro.generate_snapshot(config, results)
    with open(f"{PHASE2_DIR}/reproducibility_snapshot.json", "w") as f:
        json.dump(snap, f, indent=2, default=str)
    print("Reproducibility snapshot saved")
except Exception as e:
    print(f"Reproducibility error: {e}")
    import traceback; traceback.print_exc()

print("\nPhase 2 deliverables generated successfully!")
