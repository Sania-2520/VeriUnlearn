"""Unit tests for MLEngineClient provider reachability and vector operations."""

import httpx
import pytest
from app.infrastructure.external.ml_engine import MLEngineClient, MLEngineClientError


@pytest.fixture
def client() -> MLEngineClient:
    return MLEngineClient(base_url="http://ml-engine:8001", api_key="test-key", timeout=5)


class TestTestProvider:
    # The SSRF guard resolves the probe host with socket.getaddrinfo; in
    # offline sandboxes that fails closed (correct behaviour). These tests
    # allow the probe through the guard and exercise the reachability logic.
    def _allow_probe(self, monkeypatch):
        monkeypatch.setattr(MLEngineClient, "_host_is_public", staticmethod(lambda host: True))

    async def test_reachable_when_2xx(self, client, monkeypatch):
        self._allow_probe(monkeypatch)

        async def fake_get(url, headers=None, timeout=None):
            return httpx.Response(200, request=httpx.Request("GET", url))

        monkeypatch.setattr(client._get_client(), "get", fake_get)
        result = await client.test_provider(
            "openai", {"base_url": "https://api.openai.com/v1"}, "sk-test"
        )
        assert result["reachable"] is True
        assert result["status_code"] == 200

    async def test_unreachable_on_5xx(self, client, monkeypatch):
        self._allow_probe(monkeypatch)

        async def fake_get(url, headers=None, timeout=None):
            return httpx.Response(503, request=httpx.Request("GET", url))

        monkeypatch.setattr(client._get_client(), "get", fake_get)
        result = await client.test_provider(
            "anthropic", {"base_url": "https://api.anthropic.com/v1"}, "sk-test"
        )
        assert result["reachable"] is False
        assert result["status_code"] == 503

    async def test_unreachable_on_connection_error(self, client, monkeypatch):
        self._allow_probe(monkeypatch)

        async def fake_get(url, headers=None, timeout=None):
            raise httpx.ConnectError("connection refused")

        monkeypatch.setattr(client._get_client(), "get", fake_get)
        result = await client.test_provider("openai", {"base_url": "https://api.openai.com/v1"}, "sk-test")
        assert result["reachable"] is False
        assert "unreachable" in result["message"].lower()

    async def test_no_base_url_fails_closed(self, client):
        result = await client.test_provider("ollama", {}, None)
        assert result["reachable"] is False
        assert "base_url" in result["message"]

    async def test_default_url_for_openai(self, client, monkeypatch):
        self._allow_probe(monkeypatch)
        captured = {}

        async def fake_get(url, headers=None, timeout=None):
            captured["url"] = url
            return httpx.Response(200, request=httpx.Request("GET", url))

        monkeypatch.setattr(client._get_client(), "get", fake_get)
        await client.test_provider("openai", {}, "sk-default")
        assert captured["url"].startswith("https://api.openai.com/v1")

    async def test_credentials_sent_only_to_allowlisted_hosts(self, client, monkeypatch):
        self._allow_probe(monkeypatch)
        captured = {}

        async def fake_get(url, headers=None, timeout=None):
            captured["headers"] = headers
            return httpx.Response(200, request=httpx.Request("GET", url))

        monkeypatch.setattr(client._get_client(), "get", fake_get)
        # Allowlisted host: credentials are attached.
        await client.test_provider("openai", {"base_url": "https://api.openai.com/v1"}, "sk-secret")
        assert captured["headers"].get("Authorization") == "Bearer sk-secret"

        # Non-allowlisted host: probe runs WITHOUT credentials (no exfiltration).
        await client.test_provider("ollama", {"base_url": "https://custom.example.com/v1"}, "sk-secret")
        assert "Authorization" not in captured["headers"]
        assert "x-api-key" not in captured["headers"]

    async def test_ssrf_blocks_private_host(self, client, monkeypatch):
        # Force the guard to resolve to a private address and verify the probe
        # is blocked before any HTTP request is attempted.
        def fake_resolve(host):
            return False  # simulate non-public resolution

        monkeypatch.setattr(MLEngineClient, "_host_is_public", staticmethod(fake_resolve))
        get_called = False

        async def fake_get(url, headers=None, timeout=None):
            nonlocal get_called
            get_called = True
            return httpx.Response(200, request=httpx.Request("GET", url))

        monkeypatch.setattr(client._get_client(), "get", fake_get)
        result = await client.test_provider(
            "openai", {"base_url": "http://169.254.169.254/latest/meta-data/"}, "sk-test"
        )
        assert result["reachable"] is False
        assert "blocked" in result["message"].lower()
        assert get_called is False

    async def test_non_http_scheme_rejected(self, client):
        result = await client.test_provider(
            "openai", {"base_url": "file:///etc/passwd"}, None
        )
        assert result["reachable"] is False
        assert "http" in result["message"].lower()


class TestVectorOperations:
    async def test_upsert_embedding_posts_to_vectors_endpoint(self, client, monkeypatch):
        captured = {}

        async def fake_request(method, path, *, json=None, params=None, timeout=None, error_label="", include_headers=True):
            captured["method"] = method
            captured["path"] = path
            captured["json"] = json
            return {"success": True}

        monkeypatch.setattr(client, "_request", fake_request)
        await client.upsert_embedding(
            "memory", "point-1", [0.1, 0.2, 0.3], {"user_id": "u1"}
        )
        assert captured["path"] == "/rag/vectors/upsert"
        assert captured["json"]["collection"] == "memory"
        assert captured["json"]["point_id"] == "point-1"
        assert captured["json"]["vector"] == [0.1, 0.2, 0.3]

    async def test_delete_vectors_posts_to_delete_endpoint(self, client, monkeypatch):
        captured = {}

        async def fake_request(method, path, *, json=None, params=None, timeout=None, error_label="", include_headers=True):
            captured["method"] = method
            captured["path"] = path
            captured["json"] = json
            return {"success": True, "deleted": 3}

        monkeypatch.setattr(client, "_request", fake_request)
        await client.delete_vectors("documents", {"document_id": "d1"})
        assert captured["path"] == "/rag/vectors/delete"
        assert captured["json"]["filter"] == {"document_id": "d1"}

    async def test_request_error_propagates_as_client_error(self, client, monkeypatch):
        async def fake_request(method, path, **kwargs):
            raise MLEngineClientError("ML Engine request failed: boom")

        monkeypatch.setattr(client, "_request", fake_request)
        with pytest.raises(MLEngineClientError):
            await client.upsert_embedding("memory", "p", [1.0], {})
