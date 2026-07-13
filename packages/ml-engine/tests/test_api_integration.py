import pytest
from httpx import ASGITransport, AsyncClient

from api import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
class TestMLApiIntegration:
    async def test_health(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "sisa" in data["algorithms"]

    async def test_unlearn_small_data(self, client: AsyncClient):
        resp = await client.post("/unlearn", json={
            "target_data_ids": ["data_000000"],
            "model_name": "api_test_small",
            "data_size": 50,
            "latency_ms": 200,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["algorithm"] == "hybrid"

    async def test_unlearn_large_data_gdpr(self, client: AsyncClient):
        resp = await client.post("/unlearn", json={
            "target_data_ids": ["data_000000", "data_000001"],
            "model_name": "api_test_large",
            "data_size": 5000,
            "accuracy_target": 0.99,
            "regulatory": "gdpr",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["metrics"]) >= 2

    async def test_unlearn_returns_metrics(self, client: AsyncClient):
        resp = await client.post("/unlearn", json={
            "target_data_ids": ["data_000005"],
            "model_name": "api_test_metrics",
            "data_size": 100,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "processing_time_ms" in data
        assert data["processing_time_ms"] >= 0
        assert "utility_retained" in data

    async def test_proof_generate_and_verify(self, client: AsyncClient):
        gen_resp = await client.post("/proof/generate", json={
            "deletion_steps": ["step1", "step2", "step3"],
            "algorithm": "ed25519",
        })
        assert gen_resp.status_code == 200
        gen_data = gen_resp.json()
        assert "merkle_root" in gen_data
        assert "signature_hex" in gen_data
        assert "public_key_pem" in gen_data
        assert gen_data["leaf_count"] == 3

        verify_resp = await client.post("/proof/verify", json={
            "message": gen_data["merkle_root"],
            "signature_hex": gen_data["signature_hex"],
            "public_key_pem": gen_data["public_key_pem"],
        })
        assert verify_resp.status_code == 200
        assert verify_resp.json()["is_valid"] is True

    async def test_proof_verify_rejects_tampered(self, client: AsyncClient):
        gen_resp = await client.post("/proof/generate", json={
            "deletion_steps": ["real_data"],
            "algorithm": "ed25519",
        })
        gen_data = gen_resp.json()

        verify_resp = await client.post("/proof/verify", json={
            "message": "tampered_root",
            "signature_hex": gen_data["signature_hex"],
            "public_key_pem": gen_data["public_key_pem"],
        })
        assert verify_resp.status_code == 200
        assert verify_resp.json()["is_valid"] is False

    async def test_multiple_unlearns_preserve_algorithms(self, client: AsyncClient):
        ctx = {
            "target_data_ids": ["data_000000"],
            "model_name": "api_test_multi",
            "data_size": 100,
        }
        r1 = await client.post("/unlearn", json=ctx)
        assert r1.json()["success"] is True

        ctx["target_data_ids"] = ["data_000001"]
        r2 = await client.post("/unlearn", json=ctx)
        assert r2.json()["success"] is True
        assert r2.json()["algorithm"] == "hybrid"
