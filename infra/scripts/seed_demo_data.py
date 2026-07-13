#!/usr/bin/env python3
"""Seed the VeriUnlearn platform with demo data for evaluation and presentation.

Usage:
    python seed_demo_data.py [--api-url http://localhost:8000/api/v1]

This script populates:

  1. Sample users with API keys
  2. Uploaded datasets (CIFAR-10, CIFAR-100, TinyImageNet stubs)
  3. Base models (ResNet-18, ResNet-50, ViT-B-16 stubs)
  4. Adapters (LoRA adapters with various R/alpha values)
  5. Unlearning tasks with mock results
  6. Benchmark results for 4 algorithms across 3 datasets
  7. Explainability analyses (SHAP, LIME, Integrated Gradients)
  8. Continual learning sessions with drift events
  9. Certificate chain with proof steps
"""
import argparse
import hashlib
import json
import random
import secrets
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError:
    print("httpx is required. Install with: pip install httpx")
    sys.exit(1)

API_URL = "http://localhost:8000/api/v1"
DEMO_USER = "demo@veriunlearn.ai"
DEMO_PASS = "DemoPassword123!"

DATASETS = [
    {"id": "cifar10", "name": "CIFAR-10", "classes": 10, "samples": 50000, "size_mb": 168},
    {"id": "cifar100", "name": "CIFAR-100", "classes": 100, "samples": 50000, "size_mb": 169},
    {"id": "tiny_imagenet", "name": "TinyImageNet", "classes": 200, "samples": 100000, "size_mb": 237},
]

MODELS = [
    {"id": "resnet18", "name": "ResNet-18", "params_m": 11.2, "framework": "pytorch"},
    {"id": "resnet50", "name": "ResNet-50", "params_m": 25.6, "framework": "pytorch"},
    {"id": "vit_b16", "name": "ViT-B-16", "params_m": 86.6, "framework": "pytorch"},
]

ADAPTER_CONFIGS = [
    {"name": "LoRA-cifar10-r8", "lora_r": 8, "lora_alpha": 16, "lora_dropout": 0.1, "dataset": "cifar10", "base_model": "resnet18"},
    {"name": "LoRA-cifar10-r16", "lora_r": 16, "lora_alpha": 32, "lora_dropout": 0.1, "dataset": "cifar10", "base_model": "resnet18"},
    {"name": "LoRA-cifar100-r8", "lora_r": 8, "lora_alpha": 16, "lora_dropout": 0.1, "dataset": "cifar100", "base_model": "resnet50"},
    {"name": "LoRA-cifar100-r16", "lora_r": 16, "lora_alpha": 32, "lora_dropout": 0.1, "dataset": "cifar100", "base_model": "resnet50"},
    {"name": "LoRA-tiny-r8", "lora_r": 8, "lora_alpha": 16, "lora_dropout": 0.1, "dataset": "tiny_imagenet", "base_model": "vit_b16"},
]

UNLEARN_ALGORITHMS = ["sisa", "influence", "certified", "hybrid"]
UNLEARN_TARGETS = {ds["id"]: 100 + i * 50 for i, ds in enumerate(DATASETS)}

random.seed(42)


def _random_float(low: float, high: float, decimal: int = 4) -> float:
    return round(random.uniform(low, high), decimal)


def _random_dt(days_back: int = 30) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=random.randint(0, days_back),
                                                     hours=random.randint(0, 23))).isoformat()


def _dict_hash(d: dict) -> str:
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()[:32]


def ensure_user(client: httpx.Client) -> dict:
    r = client.post("/auth/register", json={"email": DEMO_USER, "password": DEMO_PASS})
    if r.status_code == 409:
        r = client.post("/auth/login", json={"email": DEMO_USER, "password": DEMO_PASS})
    r.raise_for_status()
    token = r.json().get("access_token") or r.json().get("token")
    client.headers["Authorization"] = f"Bearer {token}"
    return r.json()


def seed_adapters(client: httpx.Client) -> list[dict]:
    adapters = []
    for cfg in ADAPTER_CONFIGS:
        payload = {
            "name": cfg["name"],
            "base_model": cfg["base_model"],
            "dataset": cfg["dataset"],
            "lora_r": cfg["lora_r"],
            "lora_alpha": cfg["lora_alpha"],
            "lora_dropout": cfg["lora_dropout"],
            "metadata": {"version": "1.0", "description": f"Demo adapter for {cfg['dataset']}"},
        }
        r = client.post("/adapters", json=payload)
        if r.status_code == 409:
            r = client.get(f"/adapters?name={cfg['name']}")
        if r.status_code == 200 or r.status_code == 201:
            adapters.append(r.json())
        print(f"  Adapter '{cfg['name']}': {r.status_code}")
    return adapters


def seed_unlearning_tasks(client: httpx.Client, adapters: list[dict]) -> list[dict]:
    tasks = []
    for adapter in adapters:
        count = random.randint(1, 3)
        for _ in range(count):
            payload = {
                "adapter_id": adapter.get("id") or adapter.get("_id"),
                "algorithm": random.choice(UNLEARN_ALGORITHMS),
                "target_indices": [random.randint(0, 49999) for _ in range(20)],
                "dataset": adapter.get("dataset", "cifar10"),
                "config": {"batch_size": 32, "lr": 1e-4},
            }
            r = client.post("/unlearning/tasks", json=payload)
            if r.status_code in (200, 201):
                tasks.append(r.json())
            print(f"  Unlearning task ({adapter['name']}): {r.status_code}")
    return tasks


def seed_benchmark_results(client: httpx.Client) -> None:
    for ds in DATASETS:
        for algo in UNLEARN_ALGORITHMS:
            payload = {
                "dataset": ds["id"],
                "algorithm": algo,
                "accuracy": _random_float(0.72, 0.96),
                "f1_macro": _random_float(0.70, 0.95),
                "mia_success_rate": _random_float(0.08, 0.35),
                "privacy_leakage": _random_float(0.05, 0.25),
                "latency_ms": _random_float(50, 4500, 1),
                "data_size": ds["samples"],
                "deletion_fraction": _random_float(0.01, 0.10, 3),
                "forget_rate": _random_float(0.85, 0.99),
                "model_inversion_resistance": _random_float(0.80, 0.98),
                "success": True,
                "timestamp": _random_dt(),
            }
            r = client.post("/benchmarks/results", json=payload)
            print(f"  Benchmark {ds['id']}/{algo}: {r.status_code}")


def seed_explainability(client: httpx.Client) -> None:
    for ds in DATASETS:
        for method in ["shap", "lime", "integrated_gradients"]:
            payload = {
                "dataset": ds["id"],
                "method": method,
                "feature_importance": {f"feat_{i}": _random_float(-0.3, 0.5, 4) for i in range(20)},
                "top_features": [f"feat_{i}" for i in range(5)],
                "baseline_accuracy": _random_float(0.80, 0.95),
                "after_unlearning_accuracy": _random_float(0.78, 0.94),
                "privacy_impact_score": _random_float(0.0, 0.3),
                "metadata": {"samples_analyzed": 1000, "runtime_seconds": _random_float(5, 120, 1)},
                "timestamp": _random_dt(),
            }
            r = client.post("/explainability", json=payload)
            print(f"  Explainability {ds['id']}/{method}: {r.status_code}")


def seed_continual_learning(client: httpx.Client) -> None:
    for ds in DATASETS:
        payload = {
            "dataset": ds["id"],
            "session_id": str(uuid.uuid4()),
            "tasks_completed": random.randint(1, 10),
            "samples_processed": random.randint(100, 5000),
            "current_accuracy": _random_float(0.65, 0.92),
            "forgetting_rate": _random_float(0.02, 0.15),
            "drift_detected": random.choice([True, False]),
            "drift_score": _random_float(0.0, 0.8) if random.random() > 0.5 else 0.0,
            "ewc_lambda": _random_float(0.1, 10.0),
            "replay_buffer_size": random.randint(500, 5000),
            "status": "active",
            "timestamp": _random_dt(),
        }
        r = client.post("/continual-learning/sessions", json=payload)
        print(f"  Continual learning {ds['id']}: {r.status_code}")


def seed_certificates(client: httpx.Client) -> None:
    for ds in DATASETS:
        for algo in UNLEARN_ALGORITHMS:
            proof_steps = [
                {"step": i, "description": desc, "hash": secrets.token_hex(16)}
                for i, desc in enumerate([
                    "Initialize unlearning request",
                    "Load model checkpoint",
                    "Apply unlearning algorithm",
                    "Verify parameter delta",
                    "Compute inclusion test",
                    "Generate zero-knowledge proof",
                    "Submit to certificate chain",
                ])
            ]
            payload = {
                "dataset": ds["id"],
                "algorithm": algo,
                "model_id": random.choice(MODELS)["id"],
                "status": random.choice(["valid", "valid", "valid", "pending"]),
                "proof_steps": proof_steps,
                "root_hash": secrets.token_hex(32),
                "merkle_root": secrets.token_hex(32),
                "timestamp": _random_dt(),
            }
            r = client.post("/certificates", json=payload)
            print(f"  Certificate {ds['id']}/{algo}: {r.status_code}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo data for VeriUnlearn")
    parser.add_argument("--api-url", default=API_URL, help="Base API URL")
    parser.add_argument("--no-adapters", action="store_true")
    parser.add_argument("--no-unlearning", action="store_true")
    parser.add_argument("--no-benchmarks", action="store_true")
    parser.add_argument("--no-explainability", action="store_true")
    parser.add_argument("--no-continual", action="store_true")
    parser.add_argument("--no-certificates", action="store_true")
    args = parser.parse_args()

    base_url = args.api_url.rstrip("/")
    client = httpx.Client(base_url=base_url, timeout=30.0)

    print(f"Connecting to {base_url} ...")
    try:
        r = client.get("/health")
        r.raise_for_status()
        print(f"  OK (status={r.status_code})")
    except Exception as e:
        print(f"  Failed to connect: {e}")
        print("  Start the backend first: make dev-backend")
        sys.exit(1)

    print("\nStep 1/7: Creating demo user ...")
    user = ensure_user(client)
    print(f"  User: {DEMO_USER} (token={user.get('access_token', 'N/A')[:16]}...)")

    adapters = []
    if not args.no_adapters:
        print("\nStep 2/7: Seeding adapters ...")
        adapters = seed_adapters(client)

    if not args.no_unlearning and adapters:
        print("\nStep 3/7: Seeding unlearning tasks ...")
        seed_unlearning_tasks(client, adapters)

    if not args.no_benchmarks:
        print("\nStep 4/7: Seeding benchmark results ...")
        seed_benchmark_results(client)

    if not args.no_explainability:
        print("\nStep 5/7: Seeding explainability analyses ...")
        seed_explainability(client)

    if not args.no_continual:
        print("\nStep 6/7: Seeding continual learning sessions ...")
        seed_continual_learning(client)

    if not args.no_certificates:
        print("\nStep 7/7: Seeding certificates ...")
        seed_certificates(client)

    print("\nDemo data seeded successfully!")


if __name__ == "__main__":
    main()
