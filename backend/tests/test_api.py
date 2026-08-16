from __future__ import annotations

import pytest

from tests.conftest import run_unlearning_inline
from tests.test_unlearning_flow import make_csv


async def execute_dispatched(client, session_factory):
    """Run all recorded unlearning requests (after HTTP transactions commit)."""
    for request_id in list(client.dispatched):  # type: ignore[attr-defined]
        await run_unlearning_inline(session_factory, request_id)


@pytest.mark.asyncio
async def test_auth_flow(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "a@b.dev", "full_name": "Alice", "password": "password123"},
    )
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    assert token

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "a@b.dev"

    bad = await client.post("/api/v1/auth/login", json={"email": "a@b.dev", "password": "wrong"})
    assert bad.status_code == 401

    unauthed = await client.get("/api/v1/auth/me")
    assert unauthed.status_code == 401


@pytest.mark.asyncio
async def test_full_api_flow(client, auth_headers, session_factory):
    # --- ingest ---
    resp = await client.post(
        "/api/v1/datasets/upload",
        headers=auth_headers,
        data={"shard_count": "4"},
        files={"file": ("synth.csv", make_csv(400), "text/csv")},
    )
    assert resp.status_code == 201, resp.text
    dataset_id = resp.json()["id"]

    # --- train ---
    resp = await client.post(f"/api/v1/models/train?dataset_id={dataset_id}", headers=auth_headers)
    assert resp.status_code == 201, resp.text
    model_id = resp.json()["id"]
    assert resp.json()["metrics"]["accuracy"] > 0.8
    assert resp.json()["status"] == "ready"

    # --- inference ---
    resp = await client.post(
        f"/api/v1/models/{model_id}/predict",
        headers=auth_headers,
        json={"features": {"a": 2.0, "b": -2.0}},
    )
    assert resp.status_code == 200
    assert "probability" in resp.json()

    # --- privacy search ---
    resp = await client.post("/api/v1/privacy/search?query=a", headers=auth_headers)
    assert resp.status_code == 200
    matches = resp.json()["matches"]
    assert matches
    target = matches[0]

    # --- selective unlearning (background task inlined by fixture) ---
    resp = await client.post(
        "/api/v1/unlearning/selective",
        headers=auth_headers,
        json={
            "identity_key": target["identity_key"],
            "deletion_type": "records",
            "method": "retrain",
        },
    )
    assert resp.status_code == 202, resp.text
    request_id = resp.json()["id"]
    await execute_dispatched(client, session_factory)

    poll = await client.get(f"/api/v1/unlearning/requests/{request_id}", headers=auth_headers)
    assert poll.status_code == 200
    assert poll.json()["status"] == "completed"

    cert_id = poll.json()["certificate_id"]

    # --- certificate + verification ---
    cert = await client.get(f"/api/v1/certificates/{cert_id}", headers=auth_headers)
    assert cert.status_code == 200
    assert cert.json()["pre_merkle_root"] != cert.json()["post_merkle_root"]

    verify = await client.post(f"/api/v1/verification/verify/{cert_id}", headers=auth_headers)
    assert verify.status_code == 200
    assert verify.json()["verified"] is True

    pdf = await client.get(f"/api/v1/certificates/{cert_id}/pdf", headers=auth_headers)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"

    # --- compliance + audit ---
    overview = await client.get("/api/v1/compliance/overview", headers=auth_headers)
    assert overview.status_code == 200
    assert "gdpr" in overview.json()

    audit = await client.get("/api/v1/audit/verify", headers=auth_headers)
    assert audit.status_code == 200
    assert audit.json()["verified"] is True


@pytest.mark.asyncio
async def test_attacks_and_benchmark(client, auth_headers):
    resp = await client.post(
        "/api/v1/datasets/upload",
        headers=auth_headers,
        data={"shard_count": "4"},
        files={"file": ("synth.csv", make_csv(400), "text/csv")},
    )
    dataset_id = resp.json()["id"]
    resp = await client.post(f"/api/v1/models/train?dataset_id={dataset_id}", headers=auth_headers)
    model_id = resp.json()["id"]

    mia = await client.post(f"/api/v1/attacks/membership/{model_id}", headers=auth_headers)
    assert mia.status_code == 200
    assert "auc" in mia.json()

    backdoor = await client.post(
        f"/api/v1/attacks/backdoor/{model_id}", headers=auth_headers, params={"poison_fraction": 0.2}
    )
    assert backdoor.status_code == 200
    assert "trigger_fires_after_unlearning" in backdoor.json()

    inv = await client.post(f"/api/v1/attacks/inversion/{model_id}", headers=auth_headers)
    assert inv.status_code == 200

    bench = await client.post(
        f"/api/v1/benchmarks/run?dataset_id={dataset_id}&n_delete=40", headers=auth_headers
    )
    assert bench.status_code == 200, bench.text
    methods = {row["method"] for row in bench.json()["results"]}
    assert {"original", "sisa_retrain", "certified_removal", "influence_scrub"} <= methods


@pytest.mark.asyncio
async def test_full_identity_reset(client, auth_headers, session_factory):
    resp = await client.post(
        "/api/v1/datasets/upload",
        headers=auth_headers,
        data={"shard_count": "4"},
        files={"file": ("synth.csv", make_csv(400), "text/csv")},
    )
    dataset_id = resp.json()["id"]
    await client.post(f"/api/v1/models/train?dataset_id={dataset_id}", headers=auth_headers)

    search = await client.post("/api/v1/privacy/search?query=a", headers=auth_headers)
    target = search.json()["matches"][0]

    resp = await client.post(
        "/api/v1/unlearning/full-reset",
        headers=auth_headers,
        json={"identity_key": target["identity_key"]},
    )
    assert resp.status_code == 202, resp.text
    await execute_dispatched(client, session_factory)
    poll = await client.get(f"/api/v1/unlearning/requests/{resp.json()['id']}", headers=auth_headers)
    assert poll.json()["status"] == "completed"

    footprint = await client.get(
        f"/api/v1/privacy/footprint/{target['identity_key']}", headers=auth_headers
    )
    assert footprint.status_code == 200
    assert footprint.json()["active_records"] == 0
    assert footprint.json()["deleted_records"] > 0
