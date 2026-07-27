import json
import os
import csv
from collections import defaultdict

SUMMARY_PATH = r"C:\Users\sania\Desktop\PROJECT\VERIUNLEARN\evaluation\results\phase2_complete\summary.json"
RESULTS_PATH = r"C:\Users\sania\Desktop\PROJECT\VERIUNLEARN\evaluation\results\phase2_complete\results.json"
OUTPUT_DIR = r"C:\Users\sania\Desktop\PROJECT\VERIUNLEARN\docs\tables"

ALGORITHM_LABELS = {
    "retrain": "Retrain",
    "sisa": "SISA",
    "scrub": "Scrub",
    "influence_functions": "Infl. Func.",
    "fine_tune_forgetting": "Fine-tune",
}

DATASET_LABELS = {
    "mnist": "MNIST",
    "cifar10": "CIFAR-10",
    "imdb": "IMDB",
    "ag_news": "AG News",
}

ALGORITHM_INFO = [
    ("Retrain", "Complete model retraining from scratch on remaining data", "Exact",
     "Discard all parameters; retrain on remaining data", "High (full retraining)"),
    ("SISA", "Sharded, Isolated, Sliced, and Aggregated training for efficient data removal",
     "Amnesiac", "Retrain only affected shards", "Medium (shard-level retraining)"),
    ("Scrub", "Approximates unlearning by perturbing model parameters using influence-based gradients",
     "Approximate", "Gradient-based parameter perturbation", "Low (single pass)"),
    ("Infl. Func.", "Uses influence functions to estimate and reverse the effect of training points",
     "Approximate", "Influence function estimation and param. correction", "Medium (per-sample)"),
    ("Fine-tune", "Fine-tunes the model on the data remaining after forgetting",
     "Approximate", "Gradient descent on retained data", "Low (few epochs)"),
]

DATASET_INFO = [
    ("MNIST", "10", "1 x 28 x 28", "0.8 / 0.1 / 0.1", "500", "Handwritten digit recognition"),
    ("CIFAR-10", "10", "3 x 32 x 32", "0.8 / 0.1 / 0.1", "500", "Natural image classification"),
    ("IMDB", "2", "512 (seq.)", "0.8 / 0.1 / 0.1", "500", "Sentiment analysis"),
    ("AG News", "4", "256 (seq.)", "0.8 / 0.1 / 0.1", "500", "News topic classification"),
]

HYPERPARAMS = [
    ("Model", "Name", "logistic_regression"),
    ("Model", "Hidden Dimension", "128"),
    ("Model", "Number of Layers", "2"),
    ("Model", "Dropout", "0.1"),
    ("Model", "LoRA Rank", "8"),
    ("Model", "LoRA Alpha", "16"),
    ("Model", "LoRA Dropout", "0.1"),
    ("Training", "Optimizer", "AdamW"),
    ("Training", "Scheduler", "Cosine"),
    ("Training", "Learning Rate", "0.001"),
    ("Training", "Weight Decay", "0.0001"),
    ("Training", "Batch Size", "128"),
    ("Training", "Epochs", "10"),
    ("Training", "Warmup Steps", "100"),
    ("Training", "Max Grad Norm", "1.0"),
    ("Training", "Early Stopping Patience", "5"),
    ("Unlearning", "Forget Ratios", "5\\%, 10\\%, 25\\%"),
    ("Unlearning", "Runs per Config", "5"),
    ("Unlearning", "Seed Start", "42"),
    ("Privacy", "MIA Samples", "200"),
    ("Privacy", "MIA Threshold Percentile", "50\\%"),
    ("Privacy", "Leakage Bins", "50"),
    ("Privacy", "Attack Confidence", "0.95"),
]

os.makedirs(OUTPUT_DIR, exist_ok=True)

with open(SUMMARY_PATH, "r") as f:
    summary = json.load(f)

with open(RESULTS_PATH, "r") as f:
    results_config = json.load(f)["config"]

per_config = summary["per_config"]
algo_means = summary["algorithm_means"]

ALGORITHMS_ORDERED = ["retrain", "sisa", "scrub", "influence_functions", "fine_tune_forgetting"]
DATASETS_ORDERED = ["mnist", "cifar10", "imdb", "ag_news"]

def fmt(v, decimals=4):
    if v is None:
        return "---"
    if isinstance(v, float):
        if abs(v) < 0.01:
            return f"{v:.{decimals}e}"
        return f"{v:.{decimals}f}"
    return str(v)

def fmt_pct(v, decimals=2):
    if v is None:
        return "---"
    return f"{v*100:.{decimals}f}\\%"

def escape_latex(s):
    return s.replace("%", "\\%").replace("_", "\\_").replace("&", "\\&").replace("#", "\\#")

def write_latex(filename, caption, label, col_spec, header, rows):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w") as f:
        f.write("\\begin{table}[t]\n")
        f.write("\\centering\n")
        f.write(f"\\caption{{{caption}}}\n")
        f.write(f"\\label{{tab:{label}}}\n")
        f.write("\\small\n")
        f.write(f"\\begin{{tabular}}{{{col_spec}}}\n")
        f.write("\\toprule\n")
        f.write(" & ".join(header) + " \\\\\n")
        f.write("\\midrule\n")
        for row in rows:
            f.write(" & ".join(row) + " \\\\\n")
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")
        f.write("\\end{table}\n")
    print(f"  Generated {path}")

def write_csv(filename, header, rows):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  Generated {path}")

def write_md(filename, header, rows, title):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w") as f:
        f.write(f"# {title}\n\n")
        f.write("| " + " | ".join(header) + " |\n")
        f.write("| " + " | ".join("---" for _ in header) + " |\n")
        for row in rows:
            f.write("| " + " | ".join(row) + " |\n")
        f.write("\n")
    print(f"  Generated {path}")

def write_table(name, caption, label, header, rows):
    write_latex(f"{name}.tex", caption, label, "l" + "c" * (len(header) - 1), header, rows)
    write_csv(f"{name}.csv", header, rows)
    write_md(f"{name}.md", header, rows, caption)

# ---------------------------------------------------------------------------
# Table 1: Dataset Summary
# ---------------------------------------------------------------------------
ds_header = ["Dataset", "Classes", "Input Shape", "Train / Val / Test", "Max Samples", "Description"]
ds_rows = [[escape_latex(d[0]), d[1], d[2], d[3], d[4], escape_latex(d[5])] for d in DATASET_INFO]
write_table("dataset_summary", "Dataset Summary", "dataset_summary", ds_header, ds_rows)

# ---------------------------------------------------------------------------
# Table 2: Algorithm Comparison
# ---------------------------------------------------------------------------
algo_header = ["Algorithm", "Description", "Category", "Forgetting Mechanism", "Computational Cost"]
algo_rows = [[escape_latex(a[0]), escape_latex(a[1]), escape_latex(a[2]),
              escape_latex(a[3]), escape_latex(a[4])] for a in ALGORITHM_INFO]
write_table("algorithm_comparison", "Algorithm Comparison", "algorithm_comparison", algo_header, algo_rows)

# ---------------------------------------------------------------------------
# Table 3: Hyperparameters
# ---------------------------------------------------------------------------
hp_header = ["Section", "Parameter", "Value"]
hp_rows = [[h[0], escape_latex(h[1]), h[2]] for h in HYPERPARAMS]
write_latex("hyperparameters.tex", "Hyperparameter Configuration", "hyperparameters", "l l c", hp_header, hp_rows)
write_csv("hyperparameters.csv", hp_header, hp_rows)
write_md("hyperparameters.md", hp_header, hp_rows, "Hyperparameter Configuration")

# ---------------------------------------------------------------------------
# Table 4: Experimental Configuration
# ---------------------------------------------------------------------------
exp_seeds = results_config["seeds"]
exp_header = ["Setting", "Value"]
exp_rows = [
    ["Seeds", f"Global={exp_seeds['global_seed']}, NumPy={exp_seeds['numpy_seed']}, "
              f"PyTorch={exp_seeds['torch_seed']}"],
    ["Datasets", ", ".join(DATASET_LABELS.values())],
    ["Algorithms", ", ".join(ALGORITHM_LABELS.values())],
    ["Forget Ratios", "5\\%, 10\\%, 25\\%"],
    ["Runs per Config", "5"],
    ["Total Runs", str(summary["total_runs"])],
    ["Successful", str(summary["successful"])],
    ["Failed", str(summary["failed"])],
]
write_latex("experimental_config.tex", "Experimental Configuration", "experimental_config",
            "l c", exp_header, exp_rows)
write_csv("experimental_config.csv", exp_header, exp_rows)
write_md("experimental_config.md", exp_header, exp_rows, "Experimental Configuration")

# ---------------------------------------------------------------------------
# Aggregate per algorithm|dataset across forget ratios
# ---------------------------------------------------------------------------
def get_alg_dataset_mean(metric):
    """Return dict[algo][dataset] = mean value across all forget ratios."""
    result = defaultdict(lambda: defaultdict(list))
    for key, data in per_config.items():
        parts = key.split("|")
        if len(parts) != 3:
            continue
        algo, ds, fr = parts
        if metric in data:
            result[algo][ds].append(data[metric])
    agg = {}
    for algo in result:
        agg[algo] = {}
        for ds in result[algo]:
            vals = result[algo][ds]
            agg[algo][ds] = sum(vals) / len(vals) if vals else None
    return agg

METRICS_PERFORMANCE = [
    "accuracy_after_mean", "f1_after_mean", "forget_accuracy_mean", "trust_score_mean"
]
METRICS_PRIVACY = [
    "mia_success_before_mean", "mia_success_after_mean", "privacy_leakage_mean"
]
METRICS_TRUST = [
    "trust_score_mean", "utility_loss_mean", "knowledge_retention_mean"
]
METRICS_EFFICIENCY = [
    "training_time_mean", "unlearning_time_mean", "speedup_mean"
]

# ---------------------------------------------------------------------------
# Tables 5-8 helper
# ---------------------------------------------------------------------------
def build_metric_table(metrics, metric_labels):
    header = ["Algorithm"] + [DATASET_LABELS[d] for d in DATASETS_ORDERED]
    rows = []
    for algo in ALGORITHMS_ORDERED:
        row = [ALGORITHM_LABELS[algo]]
        for ds in DATASETS_ORDERED:
            agg = get_alg_dataset_mean(metrics[0] if len(metrics) == 1 else metrics[0])
            # Actually we need a separate row per metric
            pass
        rows.append(row)
    return header, rows

# Build tables 5-8: each has Algorithm x Dataset, one row per metric group
def build_multi_metric_table(metrics, metric_labels):
    """Build a table where each algorithm has a sub-row for each metric."""
    header = ["Algorithm"] + [DATASET_LABELS[d] for d in DATASETS_ORDERED]
    rows = []
    for algo in ALGORITHMS_ORDERED:
        agg = get_alg_dataset_mean(metrics[0])
        for i, metric in enumerate(metrics):
            row = [f"{ALGORITHM_LABELS[algo]} ({metric_labels[i]})"]
            for ds in DATASETS_ORDERED:
                m_agg = get_alg_dataset_mean(metric)
                val = m_agg.get(algo, {}).get(ds, None)
                row.append(fmt(val) if val is not None else "---")
            rows.append(row)
    return header, rows

# ---------------------------------------------------------------------------
# Table 5: Performance Results (accuracy_after, f1_after, forget_accuracy, trust_score)
# ---------------------------------------------------------------------------
perf_labels = ["Acc. After", "F1 After", "Forget Acc.", "Trust Score"]
perf_header, perf_rows = build_multi_metric_table(METRICS_PERFORMANCE, perf_labels)
write_table("performance_results", "Performance Results by Algorithm and Dataset",
            "performance_results", perf_header, perf_rows)

# ---------------------------------------------------------------------------
# Table 6: Privacy Results
# ---------------------------------------------------------------------------
priv_labels = ["MIA Before", "MIA After", "Privacy Leakage"]
priv_header, priv_rows = build_multi_metric_table(METRICS_PRIVACY, priv_labels)
write_table("privacy_results", "Privacy Results by Algorithm and Dataset",
            "privacy_results", priv_header, priv_rows)

# ---------------------------------------------------------------------------
# Table 7: Trust Results
# ---------------------------------------------------------------------------
trust_labels = ["Trust Score", "Utility Loss", "Knowledge Retention"]
trust_header, trust_rows = build_multi_metric_table(METRICS_TRUST, trust_labels)
write_table("trust_results", "Trust Metrics by Algorithm and Dataset",
            "trust_results", trust_header, trust_rows)

# ---------------------------------------------------------------------------
# Table 8: Efficiency Results
# ---------------------------------------------------------------------------
eff_labels = ["Train Time (s)", "Unlearn Time (s)", "Speedup"]
eff_header, eff_rows = build_multi_metric_table(METRICS_EFFICIENCY, eff_labels)
write_table("efficiency_results", "Efficiency Results by Algorithm and Dataset",
            "efficiency_results", eff_header, eff_rows)

# ---------------------------------------------------------------------------
# Table 9: Best Overall
# ---------------------------------------------------------------------------
METRICS_FOR_BEST = [
    ("accuracy_after_mean", "Accuracy After"),
    ("f1_after_mean", "F1 Score After"),
    ("forget_accuracy_mean", "Forget Accuracy"),
    ("trust_score_mean", "Trust Score"),
    ("utility_loss_mean", "Utility Loss [lower is better]"),
    ("knowledge_retention_mean", "Knowledge Retention"),
    ("mia_success_after_mean", "MIA Success After [lower is better]"),
    ("privacy_leakage_mean", "Privacy Leakage [lower is better]"),
    ("training_time_mean", "Training Time [lower is better]"),
    ("unlearning_time_mean", "Unlearning Time [lower is better]"),
    ("speedup_mean", "Speedup [higher is better]"),
]

LOWER_IS_BETTER = {"utility_loss_mean", "mia_success_after_mean", "privacy_leakage_mean",
                   "training_time_mean", "unlearning_time_mean"}

best_header = ["Metric", "Best Algorithm", "Best Value"]
best_rows = []
for metric, label in METRICS_FOR_BEST:
    agg = get_alg_dataset_mean(metric)
    best_algo = None
    best_val = None
    for algo in ALGORITHMS_ORDERED:
        values = [v for ds, v in agg.get(algo, {}).items() if v is not None]
        if not values:
            continue
        avg = sum(values) / len(values)
        if best_algo is None:
            best_algo = algo
            best_val = avg
        else:
            if metric in LOWER_IS_BETTER:
                if avg < best_val:
                    best_algo = algo
                    best_val = avg
            else:
                if avg > best_val:
                    best_algo = algo
                    best_val = avg
    best_rows.append([escape_latex(label), escape_latex(ALGORITHM_LABELS[best_algo]), fmt(best_val)])

write_latex("best_overall.tex", "Best Performing Algorithm per Metric",
            "best_overall", "l l c", best_header, best_rows)
write_csv("best_overall.csv", best_header, best_rows)
write_md("best_overall.md", best_header, best_rows, "Best Performing Algorithm per Metric")

# ---------------------------------------------------------------------------
# Table 10: Resource Usage
# ---------------------------------------------------------------------------
res_header = ["Algorithm", "Peak Memory (MB)", "CPU Usage", "GPU Usage"]
res_rows = [
    [escape_latex(ALGORITHM_LABELS[a]), "N/A", "N/A", "N/A"]
    for a in ALGORITHMS_ORDERED
]
write_latex("resource_usage.tex", "Resource Usage per Algorithm",
            "resource_usage", "l c c c", res_header, res_rows)
write_csv("resource_usage.csv", res_header, res_rows)
write_md("resource_usage.md", res_header, res_rows, "Resource Usage per Algorithm")

print(f"\nAll tables generated in {OUTPUT_DIR}")
