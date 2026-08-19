"""Load / stress test for the VeriUnlearn API (final-phase deliverable).

Spawns the real ASGI app (uvicorn subprocess) against a **fresh** SQLite DB and
hammers representative endpoints with a concurrency ramp:

    /health               (anonymous)          — health check
    /metrics              (anonymous)          — Prometheus scrape (live psutil snapshot)
    /api/v1/auth/me       (JWT)                — authenticated read
    /api/v1/datasets      (JWT)                — DB-backed authenticated read

Why this design:
  - The full middleware stack (security headers, request metrics, origin check)
    and rate limiter are active, so numbers reflect the real deployment shape.
  - The rate limiter is raised to a non-binding limit so the test measures API
    throughput, not the 100 req/min default quota (rate limiting itself is
    covered by the pytest suite).
  - A fresh DB keeps the run reproducible and leaves the dev DB untouched.

Usage:
    python scripts/load_test.py [--levels 1,5,10,25,50] [--duration 5] [--port 8765]

Output:
    - Markdown table on stdout (percentiles + throughput per endpoint/level).
    - JSON result file written to ../../docs/data/load-test-results.json
      (relative to the backend dir), for charting / the load-test report.

Dependencies: httpx (already in requirements.txt). Python >= 3.10.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
DOCS_DATA_DIR = BACKEND_DIR.parent / "docs" / "data"
TMP_DB = BACKEND_DIR / "load_test_tmp.db"

ENDPOINTS = {
    "health": ("GET", "/health", None),
    "metrics": ("GET", "/metrics", None),
    "auth/me": ("GET", "/api/v1/auth/me", "jwt"),
    "datasets": ("GET", "/api/v1/datasets", "jwt"),
}


def _pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    idx = min(len(values) - 1, int(len(values) * p / 100))
    return values[idx] * 1000  # seconds -> ms


async def _wait_healthy(base: str, timeout: float = 30.0) -> None:
    import httpx

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{base}/health")
                if resp.status_code == 200:
                    return
        except Exception:  # noqa: BLE001 - server may still be booting
            await asyncio.sleep(0.25)
    raise RuntimeError("server did not become healthy in time")


async def _register(base: str) -> str:
    """Register a throwaway operator account; returns a JWT."""
    import httpx

    email = f"loadtest-{uuid.uuid4().hex[:8]}@test.dev"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{base}/api/v1/auth/register",
            json={"email": email, "full_name": "Load Test", "password": "loadtest12345"},
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


async def _run_level(
    base: str, token: str, level: int, duration: float
) -> tuple[dict[str, dict], float]:
    """Run ``level`` concurrent workers for ``duration`` seconds.

    Each worker cycles through every endpoint so all paths see equal pressure.
    Levels are bounded by wall-clock: after ``duration`` the stop event is set,
    in-flight requests get a short drain window, and stragglers are cancelled
    and counted as errors (so no request silently disappears from the counts).
    Returns {endpoint: {"latencies": [...], "errors": N, "count": N}}, elapsed.
    """
    import httpx

    auth_headers = {"Authorization": f"Bearer {token}"}
    results: dict[str, dict] = {name: {"latencies": [], "errors": 0, "count": 0} for name in ENDPOINTS}
    stop = asyncio.Event()

    async def worker(worker_id: int) -> None:
        async with httpx.AsyncClient(timeout=15.0) as client:
            names = list(ENDPOINTS)
            # Stagger workers slightly so the ramp is smooth rather than a thundering herd.
            await asyncio.sleep(worker_id * 0.05)
            while not stop.is_set():
                for name in names:
                    method, path, auth = ENDPOINTS[name]
                    req_headers = auth_headers if auth else None
                    start = time.monotonic()
                    try:
                        resp = await asyncio.wait_for(
                            client.request(method, f"{base}{path}", headers=req_headers), timeout=15.0
                        )
                        elapsed = time.monotonic() - start
                        if resp.status_code >= 500:
                            results[name]["errors"] += 1
                        else:
                            results[name]["latencies"].append(elapsed)
                    except Exception:  # noqa: BLE001 - timeouts/conn errors count as failures
                        results[name]["errors"] += 1
                        results[name]["latencies"].append(time.monotonic() - start)
                    finally:
                        results[name]["count"] += 1

    t0 = time.monotonic()
    tasks = [asyncio.create_task(worker(i)) for i in range(level)]
    await asyncio.sleep(duration)
    stop.set()
    # Drain window: let in-flight requests land and be counted.
    _done, pending = await asyncio.wait(tasks, timeout=8.0)
    for task in pending:
        task.cancel()
        # Cancelled in-flight requests are real failures at this concurrency.
        for name in ENDPOINTS:
            results[name]["errors"] += 1
            results[name]["count"] += 1
    await asyncio.gather(*pending, return_exceptions=True)
    return results, time.monotonic() - t0


def _table_rows(results: dict[int, dict], elapsed: dict[int, float]) -> list[dict]:
    rows = []
    for level in sorted(results):
        for name, stat in sorted(results[level].items()):
            lat = stat["latencies"]
            rows.append(
                {
                    "level": level,
                    "endpoint": name,
                    "requests": stat["count"],
                    "errors": stat["errors"],
                    "req_per_s": round(stat["count"] / max(0.001, elapsed[level]), 1),
                    "p50_ms": round(_pct(lat, 50), 2),
                    "p90_ms": round(_pct(lat, 90), 2),
                    "p95_ms": round(_pct(lat, 95), 2),
                    "p99_ms": round(_pct(lat, 99), 2),
                }
            )
    return rows


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--levels", default="1,5,10,25,50", help="comma-separated concurrency levels")
    parser.add_argument("--duration", type=float, default=5.0, help="seconds per level")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    levels = [int(x) for x in args.levels.split(",") if x.strip()]

    if TMP_DB.exists():
        TMP_DB.unlink()
    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": f"sqlite+aiosqlite:///{TMP_DB.as_posix()}",
            "RATE_LIMIT_DEFAULT": "1000000/minute",  # non-binding: measure API, not quota
            "ENV": "test",
            "DEBUG": "false",
        }
    )

    proc = subprocess.Popen(  # noqa: ASYNC220 - one-time server spawn, not per-request
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(args.port), "--log-level", "warning"],
        cwd=str(BACKEND_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{args.port}"
    try:
        await _wait_healthy(base)
        token = await _register(base)
        print(f"server ready at {base} - levels {levels}, {args.duration}s each\n")

        results: dict[int, dict] = {}
        elapsed: dict[int, float] = {}
        for level in levels:
            t0 = time.monotonic()
            results[level], elapsed[level] = await _run_level(base, token, level, args.duration)
            print(f"  level {level:>3} done in {time.monotonic() - t0:.1f}s")

        rows = _table_rows(results, elapsed)
        DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)
        out_path = DOCS_DATA_DIR / "load-test-results.json"
        out_path.write_text(json.dumps({"levels": levels, "duration_s": args.duration, "rows": rows}, indent=2), encoding="utf-8")

        print("\n| Concurrency | Endpoint | Requests | Errors | req/s | p50 (ms) | p90 (ms) | p95 (ms) | p99 (ms) |")
        print("|---|---|---|---|---|---|---|---|---|")
        for r in rows:
            print(
                f"| {r['level']} | {r['endpoint']} | {r['requests']} | {r['errors']} | {r['req_per_s']} "
                f"| {r['p50_ms']} | {r['p90_ms']} | {r['p95_ms']} | {r['p99_ms']} |"
            )
        print(f"\nJSON results -> {out_path.relative_to(BACKEND_DIR.parent)}")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        if TMP_DB.exists():
            TMP_DB.unlink()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
