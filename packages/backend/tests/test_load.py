import asyncio
import time
from typing import Any

import pytest


@pytest.mark.asyncio
async def test_auth_endpoint_throughput(async_client: Any, db_session: Any) -> None:
    from app.api.v1.auth import _auth_rl
    limiter = _auth_rl.dependency
    original_max = limiter.max_requests
    limiter.max_requests = 10000

    try:
        start = time.perf_counter()
        n = 20
        tasks = []
        for i in range(n):
            payload = {
                "email": f"loadtest_{i}_{int(time.time())}@test.com",
                "password": "LoadTestPass123!",
                "full_name": f"Load Test User {i}"
            }
            tasks.append(async_client.post("/api/v1/auth/register", json=payload))
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.perf_counter() - start
        errors = [r for r in responses if isinstance(r, Exception)]
        successes = [r for r in responses if not isinstance(r, Exception)]
        print(f"\nAuth throughput: {n} requests in {elapsed:.2f}s ({n / elapsed:.1f} req/s)")
        print(f"DEBUG successes: {[s.status_code for s in successes]}")
        if successes:
            print(f"DEBUG first response text: {successes[0].text}")
        assert len(errors) == 0, f"Errors during load test: {errors}"
        assert any(r.status_code in (200, 201, 409) for r in successes)
    finally:
        limiter.max_requests = original_max


@pytest.mark.asyncio
async def test_health_endpoint_throughput(async_client: Any, db_session: Any) -> None:
    start = time.perf_counter()
    n = 50
    tasks = [async_client.get("/health/live") for _ in range(n)]
    responses = await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - start
    successes = [r for r in responses if r.status_code == 200]
    print(f"\nHealth throughput: {n} requests in {elapsed:.2f}s ({n / elapsed:.1f} req/s)")
    assert len(successes) == n, f"Expected {n} successes, got {len(successes)}"


@pytest.mark.asyncio
async def test_concurrent_auth_login(async_client: Any, db_session: Any) -> None:
    from app.api.v1.auth import _auth_rl
    limiter = _auth_rl.dependency
    original_max = limiter.max_requests
    limiter.max_requests = 10000

    try:
        email = f"concurrent_{int(time.time())}@test.com"
        reg_resp = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "Concurrent123!",
                "full_name": "Concurrent User"
            }
        )
        print(f"DEBUG register resp: {reg_resp.status_code} - {reg_resp.text}")
        payload = {"email": email, "password": "Concurrent123!"}
        n = 10
        start = time.perf_counter()
        tasks = [async_client.post("/api/v1/auth/login", json=payload) for _ in range(n)]
        responses = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start
        successes = [r for r in responses if r.status_code == 200]
        print(f"\nConcurrent login: {n} requests in {elapsed:.2f}s ({n / elapsed:.1f} req/s)")
        print(f"DEBUG login success count: {len(successes)}")
        if responses:
            print(f"DEBUG first login resp: {responses[0].status_code} - {responses[0].text}")
        assert len(successes) >= 1
    finally:
        limiter.max_requests = original_max


@pytest.mark.asyncio
async def test_api_response_time(async_client: Any, db_session: Any) -> None:
    import statistics
    times = []
    for _ in range(10):
        start = time.perf_counter()
        resp = await async_client.get("/health/live")
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
    avg = statistics.mean(times)
    p95 = sorted(times)[int(len(times) * 0.95)]
    print(f"\nAPI response times (ms): avg={avg:.1f}, p95={p95:.1f}, max={max(times):.1f}")
    assert avg < 500, f"Average response time too high: {avg:.1f}ms"
    assert p95 < 1000, f"P95 response time too high: {p95:.1f}ms"
