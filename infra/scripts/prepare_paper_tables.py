#!/usr/bin/env python3
"""Generate LaTeX-ready tables from VeriUnlearn benchmark results.

Reads benchmark summary JSON and produces publication-quality LaTeX tables
that can be included directly in a paper via \\input{}.
"""
import argparse
import json
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# LaTeX helpers
# ---------------------------------------------------------------------------

def _escape_latex(s: str) -> str:
    """Escape special LaTeX characters."""
    replacements = {
        "&": r"\&",
        "%": r"\%",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for old, new in replacements.items():
        s = s.replace(old, new)
    return s


def _fmt(val: float, precision: int = 3, bold_best: bool = False,
         is_lower_better: bool = False, best_val: float | None = None) -> str:
    """Format a float value with optional bolding of best."""
    formatted = f"{val:.{precision}f}"
    if bold_best and best_val is not None:
        if (is_lower_better and abs(val - best_val) < 1e-6) or \
           (not is_lower_better and abs(val - best_val) < 1e-6):
            formatted = r"\textbf{" + formatted + "}"
    return formatted


# ---------------------------------------------------------------------------
# Table generators
# ---------------------------------------------------------------------------

def table_main_results(summary: list[dict], algorithms: list[str]) -> str:
    """Table 1: Main benchmark results — accuracy, F1, latency, MIA."""
    datasets = sorted(set(r["dataset"] for r in summary))
    algos = sorted(set(r["algorithm"] for r in summary))
    if algorithms:
        algos = [a for a in algorithms if a in algos]

    lines = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{Benchmark results across datasets and unlearning algorithms. "
        r"Metrics are mean values over multiple runs. Best values per dataset are \textbf{bolded}.}",
        r"\label{tab:main_results}",
        r"\small",
        r"\setlength{\tabcolsep}{4pt}",
        r"\begin{tabular}{ll" + "r" * len(algos) + "}",
        r"\toprule",
        r"Dataset & Metric & " + " & ".join(
            [r"\multicolumn{1}{c}{" + _escape_latex(a.title()) + "}" for a in algos]
        ) + r" \\",
        r"\midrule",
    ]

    metrics = [
        ("Accuracy", "mean", False),
        ("F1 Score", "f1_mean", False),
        ("Latency (ms)", "latency_mean", True),
        ("MIA Success", "mia_mean", True),
    ]

    for ds in datasets:
        ds_rows = [r for r in summary if r["dataset"] == ds]
        first = True
        for metric_name, metric_key, lower_better in metrics:
            vals = {}
            for algo in algos:
                matching = [r for r in ds_rows if r["algorithm"] == algo]
                vals[algo] = matching[0][metric_key] if matching else 0.0

            best_val = min(vals.values()) if lower_better else max(vals.values())
            cells = []
            for algo in algos:
                cells.append(_fmt(vals[algo], precision=3 if metric_key != "latency_mean" else 0,
                                  bold_best=True, best_val=best_val, is_lower_better=lower_better))

            ds_label = _escape_latex(ds.upper()) if first else ""
            metric_label = metric_name
            lines.append(f"{ds_label} & {metric_label} & " + " & ".join(cells) + r" \\")
            first = False

        lines.append(r"\midrule")

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table*}",
    ])

    return "\n".join(lines)


def table_ablation_shards(ablation_points: list[dict]) -> str:
    """Table 2: Ablation — number of shards impact on SISA."""
    shard_points = [p for p in ablation_points if p.get("study") == "shard_count"]
    if not shard_points:
        return "% No shard ablation data found\n"

    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{Ablation study: impact of shard count on SISA unlearning.}",
        r"\label{tab:ablation_shards}",
        r"\small",
        r"\begin{tabular}{rcccr}",
        r"\toprule",
        r"Shards & Accuracy & F1 & Latency (ms) & Shards Affected \\",
        r"\midrule",
    ]

    for p in sorted(shard_points, key=lambda x: int(x["value"])):
        affected = p.get("extra", {}).get("shards_affected", "-")
        lines.append(
            f"{p['value']} & {_fmt(p['accuracy'])} & {_fmt(p['f1_macro'])} "
            f"& {p['latency_ms']} & {affected} \\\\"
        )

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ])

    return "\n".join(lines)


def table_ablation_epsilon(ablation_points: list[dict]) -> str:
    """Table 3: Ablation — epsilon impact on Certified Removal."""
    eps_points = [p for p in ablation_points if p.get("study") == "epsilon"]
    if not eps_points:
        return "% No epsilon ablation data found\n"

    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{Ablation study: impact of privacy budget ($\epsilon$) on Certified Removal.}",
        r"\label{tab:ablation_epsilon}",
        r"\small",
        r"\begin{tabular}{rcccr}",
        r"\toprule",
        r"$\epsilon$ & Accuracy & F1 & Latency (ms) & Noise Scale \\",
        r"\midrule",
    ]

    for p in sorted(eps_points, key=lambda x: float(x["value"])):
        noise = p.get("extra", {}).get("noise_scale", 0)
        lines.append(
            f"{p['value']:.3f} & {_fmt(p['accuracy'])} & {_fmt(p['f1_macro'])} "
            f"& {p['latency_ms']} & {_fmt(noise, 6)} \\\\"
        )

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ])

    return "\n".join(lines)


def table_ablation_dataset_size(ablation_points: list[dict]) -> str:
    """Table 4: Ablation — dataset size impact on all algorithms."""
    ds_points = [p for p in ablation_points if p.get("study") == "dataset_size"]
    if not ds_points:
        return "% No dataset size ablation data found\n"

    sizes = sorted(set(p["value"] for p in ds_points))
    algorithms = sorted(set(p.get("extra", {}).get("algorithm", "sisa") for p in ds_points))

    lines = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{Ablation study: impact of dataset size on unlearning latency (ms) across algorithms.}",
        r"\label{tab:ablation_size}",
        r"\small",
        r"\begin{tabular}{l" + "r" * len(sizes) + "}",
        r"\toprule",
        r"Algorithm & " + " & ".join([f"$n={s}$" for s in sizes]) + r" \\",
        r"\midrule",
    ]

    for algo in algorithms:
        cells = []
        for size in sizes:
            matching = [p for p in ds_points if p["value"] == size and
                        p.get("extra", {}).get("algorithm", "sisa") == algo]
            if matching and matching[0]["success"]:
                cells.append(str(matching[0]["latency_ms"]))
            else:
                cells.append("--")
        lines.append(f"{_escape_latex(algo.title())} & " + " & ".join(cells) + r" \\")

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table*}",
    ])

    return "\n".join(lines)


def table_lora_rank(ablation_points: list[dict]) -> str:
    """Table 5: Ablation — LoRA rank impact."""
    rank_points = [p for p in ablation_points if p.get("study") == "lora_rank"]
    if not rank_points:
        return "% No LoRA rank ablation data found\n"

    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{Ablation study: impact of LoRA rank on model quality and unlearning.}",
        r"\label{tab:ablation_lora}",
        r"\small",
        r"\begin{tabular}{rcccr}",
        r"\toprule",
        r"Rank & Hidden Dim & Accuracy & F1 & Latency (ms) \\",
        r"\midrule",
    ]

    for p in sorted(rank_points, key=lambda x: int(x["value"])):
        hidden = p.get("extra", {}).get("hidden_dim", "-")
        lines.append(
            f"{p['value']} & {hidden} & {_fmt(p['accuracy'])} & {_fmt(p['f1_macro'])} "
            f"& {p['latency_ms']} \\\\"
        )

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ])

    return "\n".join(lines)


def table_privacy_summary(summary: list[dict]) -> str:
    """Table 6: Privacy comparison across algorithms."""
    algos = sorted(set(r["algorithm"] for r in summary))
    datasets = sorted(set(r["dataset"] for r in summary))

    lines = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{Privacy evaluation: membership inference attack success rate (lower is better for privacy).}",
        r"\label{tab:privacy}",
        r"\small",
        r"\begin{tabular}{l" + "r" * len(datasets) + "}",
        r"\toprule",
        r"Algorithm & " + " & ".join([_escape_latex(d.upper()) for d in datasets]) + r" \\",
        r"\midrule",
    ]

    for algo in algos:
        cells = []
        for ds in datasets:
            matching = [r for r in summary if r["dataset"] == ds and r["algorithm"] == algo]
            val = matching[0]["mia_mean"] if matching else 0.0
            cells.append(_fmt(val, bold_best=True, is_lower_better=True,
                              best_val=min(
                                  r["mia_mean"] for r in summary
                                  if r["dataset"] == ds
                              ) if any(r["dataset"] == ds for r in summary) else 0))
        lines.append(f"{_escape_latex(algo.title())} & " + " & ".join(cells) + r" \\")

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table*}",
    ])

    return "\n".join(lines)


def generate_preamble() -> str:
    """Generate a LaTeX preamble snippet for table compilation."""
    return r"""% VeriUnlearn Paper Tables
% Include this preamble in your document:
%
% \usepackage{booktabs}
% \usepackage{multirow}
% \usepackage{graphicx}
%
% To compile standalone:
% \documentclass{article}
% \usepackage{booktabs}
% \usepackage{multirow}
% \usepackage[margin=1in]{geometry}
% \begin{document}
"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate LaTeX tables for VeriUnlearn paper")
    p.add_argument("--summary", type=str, default=None,
                    help="Path to benchmark summary JSON")
    p.add_argument("--ablation", type=str, default=None,
                    help="Path to ablation results JSON")
    p.add_argument("--output-dir", type=str, default=None,
                    help="Output directory for .tex files")
    p.add_argument("--algorithms", nargs="+", default=None,
                    help="Algorithms to include in main table")
    return p.parse_args()


def _find_latest(results_dir: Path, pattern: str) -> Path | None:
    matches = sorted(results_dir.glob(pattern), reverse=True)
    return matches[0] if matches else None


def main() -> None:
    args = parse_args()

    results_dir = Path(args.output_dir) if args.output_dir else (
        _SCRIPT_DIR.parent / "benchmark_results"
    )
    results_dir.mkdir(parents=True, exist_ok=True)

    out_dir = results_dir / "latex"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load summary
    summary: list[dict] = []
    if args.summary:
        summary = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    else:
        latest = _find_latest(results_dir, "benchmark_summary_*.json")
        if latest:
            print(f"Using summary: {latest.name}")
            summary = json.loads(latest.read_text(encoding="utf-8"))
        else:
            # Try raw results and build summary
            raw_path = _find_latest(results_dir, "benchmark_*.json")
            if raw_path and "summary" not in raw_path.name:
                raw = json.loads(raw_path.read_text(encoding="utf-8"))
                from collections import defaultdict
                grouped: dict[tuple, list] = defaultdict(list)
                for r in raw:
                    grouped[(r["dataset"], r["algorithm"])].append(r)
                for (ds, algo), runs in grouped.items():
                    accs = [r["accuracy"] for r in runs if r.get("success")]
                    if accs:
                        import numpy as np
                        summary.append({
                            "dataset": ds,
                            "algorithm": algo,
                            "mean": float(np.mean(accs)),
                            "latency_mean": float(np.mean([r["latency_ms"] for r in runs])),
                            "f1_mean": float(np.mean([r["f1_macro"] for r in runs])),
                            "mia_mean": float(np.mean([r["mia_success_rate"] for r in runs])),
                            "privacy_leakage_mean": float(np.mean([r["privacy_leakage"] for r in runs])),
                        })

    # Load ablation
    ablation: list[dict] = []
    if args.ablation:
        ablation = json.loads(Path(args.ablation).read_text(encoding="utf-8"))
    else:
        ablation_dir = results_dir / "ablation"
        if ablation_dir.exists():
            abl_path = _find_latest(ablation_dir, "ablation_*.json")
            if abl_path:
                print(f"Using ablation: {abl_path.name}")
                ablation = json.loads(abl_path.read_text(encoding="utf-8"))

    print(f"Generating LaTeX tables -> {out_dir}")

    tables: dict[str, str] = {}

    if summary:
        tables["main_results.tex"] = table_main_results(summary, args.algorithms or [])
        tables["privacy_summary.tex"] = table_privacy_summary(summary)
    else:
        print("  Warning: No summary data, skipping main tables")

    if ablation:
        tables["ablation_shards.tex"] = table_ablation_shards(ablation)
        tables["ablation_epsilon.tex"] = table_ablation_epsilon(ablation)
        tables["ablation_dataset_size.tex"] = table_ablation_dataset_size(ablation)
        tables["ablation_lora_rank.tex"] = table_lora_rank(ablation)
    else:
        print("  Warning: No ablation data, skipping ablation tables")

    # Preamble
    preamble_path = out_dir / "preamble.tex"
    preamble_path.write_text(generate_preamble(), encoding="utf-8")
    print("  Saved: preamble.tex")

    # Combined file
    combined_path = out_dir / "all_tables.tex"
    combined_parts = [generate_preamble(), ""]
    for name, content in tables.items():
        content_path = out_dir / name
        content_path.write_text(content, encoding="utf-8")
        print(f"  Saved: {name}")
        combined_parts.append(f"% === {name} ===")
        combined_parts.append(content)
        combined_parts.append("")

    combined_path.write_text("\n".join(combined_parts), encoding="utf-8")
    print("  Saved: all_tables.tex (combined)")

    print(f"\nDone. Include in your paper: \\input{{{out_dir / 'main_results.tex'}}}")


if __name__ == "__main__":
    main()
