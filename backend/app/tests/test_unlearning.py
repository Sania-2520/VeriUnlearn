from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.services.proof_verification_service import ProofVerificationService


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict:
    await client.post("/api/v1/auth/register", json={
        "username": "unlearnuser",
        "email": "unlearn@example.com",
        "password": "testpassword123",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "username": "unlearnuser",
        "password": "testpassword123",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_unlearning_benchmark(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/unlearning/benchmark",
        json={
            "dataset_size": 1000,
            "num_deleted": 25,
            "sensitivity": "medium",
            "latency_budget": 300,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["recommended"] in {"certified_removal", "gradient_ascent", "influence_functions", "sisa"}
    assert data["deletion_ratio"] == 0.025
    assert len(data["algorithms"]) == 7
    assert any(a["recommended"] for a in data["algorithms"])


@pytest.mark.asyncio
async def test_unlearning_benchmark_requires_auth(client: AsyncClient):
    response = await client.post(
        "/api/v1/unlearning/benchmark",
        json={"dataset_size": 1000, "num_deleted": 25},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_execute_unlearning_returns_phase4_metadata(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/v1/unlearning/requests",
        json={
            "sample_ids": [1, 2, 3],
            "algorithm": "gradient_ascent",
            "reason": "test phase 4 execution",
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    request_id = create.json()["id"]

    execute = await client.post(
        f"/api/v1/unlearning/requests/{request_id}/execute",
        headers=auth_headers,
    )
    assert execute.status_code == 200
    assert execute.json()["status"] == "completed"

    result = await client.get(
        f"/api/v1/unlearning/results/{request_id}",
        headers=auth_headers,
    )
    assert result.status_code == 200
    data = result.json()
    assert data["algorithm"] == "gradient_ascent"
    assert data["execution_mode"] == "virtual_gradient_ascent"
    assert data["simulated"] is True
    assert data["guarantees"] == "approximate_forgetting"
    assert data["model_version_after_id"] is not None
    assert data["merkle_root"]
    assert data["signature"]
    assert data["privacy_score"] > 0
    assert data["estimated_latency"] > 0

    verification = await client.get(
        f"/api/v1/unlearning/results/{request_id}/verify",
        headers=auth_headers,
    )
    assert verification.status_code == 200
    proof = verification.json()
    assert proof["verified"] is True
    assert proof["merkle_valid"] is True
    assert proof["signature_valid"] is True
    assert proof["certificate_valid"] is True
    assert proof["certificate_hash_valid"] is True
    assert proof["certificate_signature_valid"] is True

    download = await client.get(
        f"/api/v1/unlearning/results/{request_id}/certificate",
        headers=auth_headers,
    )
    assert download.status_code == 200
    cert = download.json()
    assert cert["certificate_id"]
    assert cert["merkle_root"] == proof["result_id"] or cert["merkle_root"]

    offline = ProofVerificationService().verify_certificate_file(data["certificate_path"])
    assert offline["verified"] is True
    assert offline["certificate_hash_valid"] is True
    assert offline["certificate_signature_valid"] is True

    embedded_key = cert["public_key"]
    pinned = ProofVerificationService().verify_certificate_file(
        data["certificate_path"], pinned_public_key=embedded_key
    )
    assert pinned["verified"] is True
    assert pinned["public_key_matched"] is True

    wrong = ProofVerificationService().verify_certificate_file(
        data["certificate_path"], pinned_public_key="00" * 32
    )
    assert wrong["verified"] is False
    assert wrong["public_key_matched"] is False
    assert offline["certificate_hash_valid"] is True
    assert offline["certificate_signature_valid"] is True
