#!/usr/bin/env python3
"""Generate static demo assets for the VeriUnlearn platform.

This script regenerates all JSON artifacts under ``demo/`` so they are
reproducible (fixed seed) and match the canonical entities defined in
``infra/scripts/seed_demo_data.py``.

Stdlib only. Runs on Python 3.10+.

Usage:
    python scripts/generate_demo_assets.py
"""
from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = REPO_ROOT / "demo"
DEMO_USER = "demo@veriunlearn.ai"

DATASETS = [
    {"id": "cifar10", "name": "CIFAR-10", "classes": 10, "samples": 50000, "size_mb": 168},
    {"id": "cifar100", "name": "CIFAR-100", "classes": 100, "samples": 50000, "size_mb": 169},
    {"id": "tiny_imagenet", "name": "TinyImageNet", "classes": 200, "samples": 100000, "size_mb": 237},
]

MODELS = [
    {"id": "resnet18", "name": "ResNet-18", "params_m": 11.2, "top1_accuracy": 0.93},
    {"id": "resnet50", "name": "ResNet-50", "params_m": 25.6, "top1_accuracy": 0.76},
    {"id": "vit_b16", "name": "ViT-B-16", "params_m": 86.6, "top1_accuracy": 0.84},
]

ALGORITHMS = ["sisa", "influence", "certified", "hybrid"]

PROOF_STEP_DESCRIPTIONS = [
    "Initialize unlearning request",
    "Load model checkpoint",
    "Apply unlearning algorithm",
    "Verify parameter delta",
    "Compute inclusion test",
    "Generate zero-knowledge proof",
    "Submit to certificate chain",
]


def _fixed_dt(days_back: int, salt: int) -> str:
    """Deterministic timestamp derived from a fixed base date + salt."""
    base = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    offset = timedelta(days=days_back, hours=salt % 24, minutes=(salt * 7) % 60)
    return (base - offset).isoformat()


def _sha64(seed_str: str) -> str:
    return hashlib.sha256(seed_str.encode()).hexdigest()


def _rf(rng: random.Random, low: float, high: float, decimal: int = 4) -> float:
    return round(rng.uniform(low, high), decimal)


def build_datasets() -> dict[str, dict]:
    out: dict[str, dict] = {}
    meta = {
        "cifar10": {
            "description": "60,000 32x32 color images across 10 mutually exclusive classes. Standard benchmark for machine-unlearning evaluations.",
            "labels": ["airplane", "automobile", "bird", "cat", "deer", "dog", "frog", "horse", "ship", "truck"],
            "features_dim": 3072,
        },
        "cifar100": {
            "description": "60,000 32x32 color images across 100 fine-grained classes (20 superclasses). Higher class granularity stress-tests unlearning precision.",
            "labels": [f"class_{i:02d}" for i in range(100)],
            "features_dim": 3072,
        },
        "tiny_imagenet": {
            "description": "100,000 64x64 color images across 200 ImageNet classes. Larger-scale benchmark for scalable unlearning verification.",
            "labels": [f"n{i:08d}" for i in range(200)],
            "features_dim": 12288,
        },
    }
    for ds in DATASETS:
        m = meta[ds["id"]]
        out[ds["id"]] = {
            "id": ds["id"],
            "name": ds["name"],
            "classes": ds["classes"],
            "samples": ds["samples"],
            "size_mb": ds["size_mb"],
            "modality": "image",
            "description": m["description"],
            "sample_labels": m["labels"],
            "example_record": {
                "id": f"{ds['id']}-00000001",
                "label": m["labels"][0],
                "features_dim": m["features_dim"],
            },
            "source_license": "MIT" if ds["id"] != "tiny_imagenet" else "Custom (non-commercial)",
            "split": {"train": int(ds["samples"] * 0.9), "test": int(ds["samples"] * 0.1)},
        }
    return out


def build_models() -> dict[str, dict]:
    out: dict[str, dict] = {}
    arch = {
        "resnet18": "ResNet-18 (convolutional, 18 layers)",
        "resnet50": "ResNet-50 (convolutional, 50 layers)",
        "vit_b16": "Vision Transformer Base (patch size 16)",
    }
    train_ds = {"resnet18": "cifar10", "resnet50": "cifar100", "vit_b16": "tiny_imagenet"}
    for m in MODELS:
        out[m["id"]] = {
            "id": m["id"],
            "name": m["name"],
            "framework": "pytorch",
            "params_m": m["params_m"],
            "architecture": arch[m["id"]],
            "pretrained_source": "torchvision",
            "license": "Apache-2.0",
            "supported_adapters": ["lora"],
            "training_dataset": train_ds[m["id"]],
            "top1_accuracy": m["top1_accuracy"],
            "created_at": _fixed_dt(120, hash(m["id"]) % 30),
        }
    return out


def build_deletion_requests() -> list[dict]:
    rng = random.Random(7)
    adapters = ["LoRA-cifar10-r8", "LoRA-cifar100-r16", "LoRA-tiny-r8", "LoRA-cifar10-r16", "LoRA-cifar100-r8"]
    datasets = ["cifar10", "cifar100", "tiny_imagenet"]
    algos = ALGORITHMS
    statuses = ["completed", "verified", "in_progress", "completed", "verified"]
    cert_ids = ["cert-sisa-cifar10", "cert-certified-cifar10", None, "cert-influence-cifar10", "cert-hybrid-cifar10"]
    reqs = []
    for i in range(5):
        req_id = f"del-req-{_sha64(f'req-{i}')[:12]}"
        submitted = _fixed_dt(40 - i * 5, i * 3)
        completed = None if statuses[i] == "in_progress" else _fixed_dt(38 - i * 5, i * 3 + 1)
        reqs.append({
            "request_id": req_id,
            "user_email": DEMO_USER,
            "dataset": datasets[i % len(datasets)],
            "adapter_name": adapters[i],
            "algorithm": algos[i % len(algos)],
            "target_indices": sorted(rng.sample(range(0, 49999), 5)),
            "reason": "GDPR Art.17 erasure",
            "status": statuses[i],
            "submitted_at": submitted,
            "completed_at": completed,
            "verification_certificate_id": cert_ids[i],
        })
    return reqs


def build_certificates() -> list[dict]:
    certs = []
    for i, algo in enumerate(ALGORITHMS):
        rng = random.Random(100 + i)
        proof_steps = [
            {"step": s, "description": desc, "hash": _sha64(f"{algo}-cifar10-step-{s}")[:32]}
            for s, desc in enumerate(PROOF_STEP_DESCRIPTIONS)
        ]
        issued = _fixed_dt(30 - i * 2, i)
        expires = (datetime.fromisoformat(issued) + timedelta(days=365)).isoformat()
        certs.append({
            "certificate_id": f"cert-{algo}-cifar10",
            "dataset": "cifar10",
            "algorithm": algo,
            "model_id": "resnet18",
            "status": "valid",
            "root_hash": _sha64(f"{algo}-cifar10-root"),
            "merkle_root": _sha64(f"{algo}-cifar10-merkle"),
            "proof_steps": proof_steps,
            "inclusion_test_passed": True,
            "exclusion_verified": True,
            "issued_at": issued,
            "expires_at": expires,
            "signer": "veriunlearn-verifier",
        })
    return certs


def build_benchmark_report() -> dict:
    rng = random.Random(2026)
    results = []
    for ds in DATASETS:
        for algo in ALGORITHMS:
            seed_base = ds["samples"] + ALGORITHMS.index(algo) * 7
            r = random.Random(seed_base)
            results.append({
                "dataset": ds["id"],
                "algorithm": algo,
                "accuracy": _rf(r, 0.72, 0.96),
                "f1_macro": _rf(r, 0.70, 0.95),
                "mia_success_rate": _rf(r, 0.08, 0.35),
                "privacy_leakage": _rf(r, 0.05, 0.25),
                "latency_ms": _rf(r, 50, 4500, 1),
                "deletion_fraction": _rf(r, 0.01, 0.10, 3),
                "forget_rate": _rf(r, 0.85, 0.99),
                "model_inversion_resistance": _rf(r, 0.80, 0.98),
                "success": True,
            })
    return {
        "report_id": f"bench-report-{_sha64('benchmark-report')[:12]}",
        "generated_at": _fixed_dt(5, 0),
        "datasets": [d["id"] for d in DATASETS],
        "algorithms": ALGORITHMS,
        "results": results,
        "summary": {
            "best_algorithm_by_privacy": "certified",
            "avg_forget_rate": 0.93,
            "avg_mia_success_rate": 0.18,
        },
    }


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    random.seed(42)
    written = []

    datasets = build_datasets()
    for ds_id, ds in datasets.items():
        p = DEMO_DIR / "datasets" / f"{ds_id}.json"
        _write_json(p, ds)
        written.append(p)

    models = build_models()
    for m_id, m in models.items():
        p = DEMO_DIR / "models" / f"{m_id}.json"
        _write_json(p, m)
        written.append(p)

    reqs = build_deletion_requests()
    p = DEMO_DIR / "deletion-requests" / "sample-requests.json"
    _write_json(p, reqs)
    written.append(p)

    certs = build_certificates()
    p = DEMO_DIR / "verification-certificates" / "sample-certificates.json"
    _write_json(p, certs)
    written.append(p)

    report = build_benchmark_report()
    p = DEMO_DIR / "benchmark-reports" / "sample-report.json"
    _write_json(p, report)
    written.append(p)

    print("VeriUnlearn demo assets generated.")
    print(f"  datasets: {len(datasets)}")
    print(f"  models: {len(models)}")
    print(f"  deletion requests: {len(reqs)}")
    print(f"  verification certificates: {len(certs)}")
    print(f"  benchmark results: {len(report['results'])}")
    print(f"Total files written: {len(written)}")
    for w in written:
        print(f"  - {w.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
