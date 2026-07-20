#!/usr/bin/env python3
"""Seed the VeriUnlearn platform with demo data for evaluation and presentation.

Usage:
    python seed_demo_data.py [--api-url http://localhost:8000/api/v1]

This script populates demo content through the public REST API. Endpoints that
depend on the ML Engine (adapters, explainability, continual learning, proof
generation) will be attempted and, if the engine is unavailable (HTTP 502), the
step is skipped with a warning rather than failing the whole run.

Demo data created:
  1. Demo user (demo@veriunlearn.ai / DemoPassword123!)
  2. Adapters (LoRA configs) via /adapters/register
  3. Unlearning requests via /unlearning/requests
  4. Explainability samples via /explain/samples
  5. Continual learning tasks via /continual-learning/tasks
  6. Verification proofs via /verify/proofs/generate (when a request exists)

Note: benchmark results are produced by running the benchmark suite
(`make benchmark` / `infra/scripts/run_benchmarks.py`), not seeded here.
"""
import argparse
import random
import secrets
import sys
import uuid
from datetime import datetime, timedelta, timezone
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

random.seed(42)


def _random_float(low: float, high: float, decimal: int = 4) -> float:
    return round(random.uniform(low, high), decimal)


def _random_dt(days_back: int = 30) -> str:
    return (
        datetime.now(timezone.utc)
        - timedelta(days=random.randint(0, days_back), hours=random.randint(0, 23))
    ).isoformat()


def _ok(status: int) -> bool:
    return status in (200, 201, 202, 204)


def _skip_on_ml_engine(r: httpx.Response, label: str) -> bool:
    """Return True if the step was skipped (ML engine down / not found)."""
    if r.status_code == 502:
        print(f"  {label}: SKIPPED (ML Engine unavailable: 502)")
        return True
    if r.status_code == 404:
        print(f"  {label}: SKIPPED (endpoint not available: 404)")
        return True
    return False


def ensure_user(client: httpx.Client) -> dict:
    r = client.post(
        "/auth/register",
        json={"email": DEMO_USER, "password": DEMO_PASS, "full_name": "Demo User"},
    )
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
            "adapter_name": cfg["name"],
            "adapter_path": f"/models/{cfg['name']}",
            "base_model_name": cfg["base_model"],
            "config": {
                "lora_r": cfg["lora_r"],
                "lora_alpha": cfg["lora_alpha"],
                "lora_dropout": cfg["lora_dropout"],
                "dataset": cfg["dataset"],
            },
            "tags": {"dataset": cfg["dataset"], "base_model": cfg["base_model"]},
        }
        r = client.post("/adapters/register", json=payload)
        if _skip_on_ml_engine(r, f"Adapter '{cfg['name']}'"):
            continue
        if _ok(r.status_code):
            try:
                adapters.append(r.json())
            except Exception:
                pass
        print(f"  Adapter '{cfg['name']}': {r.status_code}")
    return adapters


def seed_unlearning_requests(client: httpx.Client, adapters: list[dict]) -> list[str]:
    request_ids: list[str] = []
    targets = [a.get("adapter_name") for a in adapters] or [d["id"] for d in DATASETS]
    for target in targets:
        algo = random.choice(UNLEARN_ALGORITHMS)
        r = client.post(
            "/unlearning/requests",
            params={
                "target_type": "adapter",
                "target_id": target,
                "reason": "Demo right-to-be-forgotten request",
                "gdpr_article": "Art. 17",
                "priority": "normal",
                "algorithm": algo,
            },
        )
        if _skip_on_ml_engine(r, f"Unlearning request ({target})"):
            continue
        if _ok(r.status_code):
            try:
                request_ids.append(r.json().get("request_id") or r.json().get("id"))
            except Exception:
                pass
        print(f"  Unlearning request ({target}/{algo}): {r.status_code}")
    return request_ids


def seed_explainability(client: httpx.Client) -> None:
    n_feat = 20
    feature_names = [f"feat_{i}" for i in range(n_feat)]
    samples = [[_random_float(-1, 1) for _ in range(n_feat)] for _ in range(16)]
    for method in ["shap", "lime", "integrated_gradients"]:
        payload = {"samples": samples, "feature_names": feature_names, "method": method}
        r = client.post("/explain/samples", json=payload)
        if _skip_on_ml_engine(r, f"Explainability/{method}"):
            continue
        print(f"  Explainability/{method}: {r.status_code}")


def seed_continual_learning(client: httpx.Client) -> None:
    for ds in DATASETS:
        task_id = f"demo-{ds['id']}-{uuid.uuid4().hex[:8]}"
        payload = {
            "task_id": task_id,
            "metadata": {
                "dataset": ds["id"],
                "samples_processed": random.randint(100, 5000),
                "current_accuracy": _random_float(0.65, 0.92),
                "forgetting_rate": _random_float(0.02, 0.15),
                "drift_detected": random.choice([True, False]),
                "drift_score": _random_float(0.0, 0.8) if random.random() > 0.5 else 0.0,
                "ewc_lambda": _random_float(0.1, 10.0),
                "replay_buffer_size": random.randint(500, 5000),
            },
        }
        r = client.post("/continual-learning/tasks", json=payload)
        if _skip_on_ml_engine(r, f"Continual learning {ds['id']}"):
            continue
        print(f"  Continual learning {ds['id']}: {r.status_code}")


def seed_proofs(client: httpx.Client, request_ids: list[str]) -> None:
    if not request_ids:
        print("  No unlearning requests available; skipping proof generation.")
        return
    for req_id in request_ids:
        deletion_steps = [secrets.token_hex(8) for _ in range(4)]
        leaves = [secrets.token_hex(16) for _ in range(4)]
        r = client.post(
            "/verify/proofs/generate",
            params={
                "job_id": f"demo-job-{uuid.uuid4().hex[:8]}",
                "request_id": req_id,
                "deletion_steps": deletion_steps,
                "algorithm": "ed25519",
            },
            json={"all_leaves": leaves, "hash_algorithm": "sha3_256"},
        )
        if _skip_on_ml_engine(r, f"Proof ({req_id})"):
            continue
        print(f"  Proof ({req_id}): {r.status_code}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo data for VeriUnlearn")
    parser.add_argument("--api-url", default=API_URL, help="Base API URL (incl. /api/v1)")
    parser.add_argument("--no-adapters", action="store_true")
    parser.add_argument("--no-unlearning", action="store_true")
    parser.add_argument("--no-explainability", action="store_true")
    parser.add_argument("--no-continual", action="store_true")
    parser.add_argument("--no-proofs", action="store_true")
    args = parser.parse_args()

    base_url = args.api_url.rstrip("/")
    client = httpx.Client(base_url=base_url, timeout=30.0)
    root_url = base_url
    if root_url.endswith("/api/v1"):
        root_url = root_url[: -len("/api/v1")]

    print(f"Connecting to {base_url} ...")
    try:
        r = client.get(f"{root_url}/health")
        r.raise_for_status()
        print(f"  OK (status={r.status_code})")
    except Exception as e:
        print(f"  Failed to connect: {e}")
        print("  Start the backend first: make dev-backend")
        sys.exit(1)

    print("\nStep 1/6: Creating demo user ...")
    user = ensure_user(client)
    print(f"  User: {DEMO_USER} (token={str(user.get('access_token', 'N/A'))[:16]}...)")

    adapters: list[dict] = []
    if not args.no_adapters:
        print("\nStep 2/6: Registering adapters ...")
        adapters = seed_adapters(client)

    request_ids: list[str] = []
    if not args.no_unlearning:
        print("\nStep 3/6: Creating unlearning requests ...")
        request_ids = seed_unlearning_requests(client, adapters)

    if not args.no_explainability:
        print("\nStep 4/6: Seeding explainability samples ...")
        seed_explainability(client)

    if not args.no_continual:
        print("\nStep 5/6: Seeding continual learning tasks ...")
        seed_continual_learning(client)

    if not args.no_proofs:
        print("\nStep 6/6: Generating verification proofs ...")
        seed_proofs(client, request_ids)

    print("\nDemo data seeding complete.")


if __name__ == "__main__":
    main()
