import asyncio
import time
from typing import Any

import pytest


@pytest.mark.asyncio
async def test_auth_endpoint_throughput(async_client: Any, db_session: Any) -> None:
    payload = {"email": "loadtest@test.com", "password": "LoadTestPass123!"}
    start = time.perf_counter()
    n = 20
    tasks = []
    for _ in range(n):
        tasks.append(async_client.post("/api/v1/auth/register", json=payload))
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = time.perf_counter() - start
    errors = [r for r in responses if isinstance(r, Exception)]
    successes = [r for r in responses if not isinstance(r, Exception)]
    print(f"\nAuth throughput: {n} requests in {elapsed:.2f}s ({n / elapsed:.1f} req/s)")
    assert len(errors) == 0, f"Errors during load test: {errors}"
    assert any(r.status_code in (200, 201, 409) for r in successes)


@pytest.mark.asyncio
async def test_health_endpoint_throughput(async_client: Any, db_session: Any) -> None:
    start = time.perf_counter()
    n = 50
    tasks = [async_client.get("/api/v1/health/liveness") for _ in range(n)]
    responses = await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - start
    successes = [r for r in responses if r.status_code == 200]
    print(f"\nHealth throughput: {n} requests in {elapsed:.2f}s ({n / elapsed:.1f} req/s)")
    assert len(successes) == n, f"Expected {n} successes, got {len(successes)}"


@pytest.mark.asyncio
async def test_concurrent_auth_login(async_client: Any, db_session: Any) -> None:
    email = f"concurrent_{int(time.time())}@test.com"
    await async_client.post("/api/v1/auth/register", json={"email": email, "password": "Concurrent123!"})
    payload = {"email": email, "password": "Concurrent123!"}
    n = 10
    start = time.perf_counter()
    tasks = [async_client.post("/api/v1/auth/login", json=payload) for _ in range(n)]
    responses = await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - start
    successes = [r for r in responses if r.status_code == 200]
    print(f"\nConcurrent login: {n} requests in {elapsed:.2f}s ({n / elapsed:.1f} req/s)")
    assert len(successes) >= 1


@pytest.mark.asyncio
async def test_api_response_time(async_client: Any, db_session: Any) -> None:
    import statistics
    times = []
    for _ in range(10):
        start = time.perf_counter()
        resp = await async_client.get("/api/v1/health/liveness")
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
    avg = statistics.mean(times)
    p95 = sorted(times)[int(len(times) * 0.95)]
    print(f"\nAPI response times (ms): avg={avg:.1f}, p95={p95:.1f}, max={max(times):.1f}")
    assert avg < 500, f"Average response time too high: {avg:.1f}ms"
    assert p95 < 1000, f"P95 response time too high: {p95:.1f}ms"
