"""Async HTTP client for the VeriUnlearn ML Engine.

Refactored so that all HTTP plumbing (connection pooling, error handling,
header injection) lives in a single ``_request`` helper backed by a shared,
per-event-loop ``httpx.AsyncClient``. Public method signatures, request paths,
payloads, and error types are identical to the previous implementation.

Connection pooling: an ``httpx.AsyncClient`` is created lazily and keyed by the
running event loop, so requests issued from the same loop (e.g. all FastAPI
handlers) reuse TCP/TLS connections and keep-alive sockets. Celery tasks run
coroutines on fresh loops, so each task gets its own client (avoids
cross-loop reuse of pooled connections). ``aclose()`` releases all resources.
"""

import asyncio
import random
from typing import Any, AsyncGenerator, Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_HTTPX_LIMITS = httpx.Limits(max_connections=100, max_keepalive_connections=20)


def _backoff_with_jitter(base: float, exponent: int, jitter_max: float = 0.25) -> float:
    """Exponential backoff with random jitter.

    Jitter is non-cryptographic (B311 is acceptable here); it only needs to
    de-synchronise concurrent retry storms, not provide unpredictability.
    """
    return base * (2 ** exponent) + random.uniform(0, jitter_max)  # nosec B311


class MLEngineClientError(Exception):
    """Raised when the ML Engine cannot fulfil a request.

    ``status_code`` is the HTTP status of the engine's response when the
    failure is an HTTP error, or ``None`` when the failure is a transport/
    connection-level error. Callers (e.g. Celery tasks) use it to decide
    whether a retry is worthwhile: ``None``, 429 and 5xx are transient;
    4xx (other than 429) are permanent.
    """

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code

    @property
    def is_transient(self) -> bool:
        if self.status_code is None:
            return True
        return self.status_code in (408, 425, 429) or self.status_code >= 500


class MLEngineClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: int = 300) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._retries = 2
        self._retry_backoff = 0.5
        self._headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            self._headers["X-API-Key"] = api_key
        self._clients: dict[int, httpx.AsyncClient] = {}

    def _build_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self._timeout,
            limits=_HTTPX_LIMITS,
            headers=self._headers,
        )

    def _get_client(self) -> httpx.AsyncClient:
        """Return a pooled client bound to the current event loop."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None:
            client = self._clients.get(id(loop))
            if client is not None and not client.is_closed:
                return client
            client = self._build_client()
            self._clients[id(loop)] = client
            return client
        client = self._build_client()
        self._clients[-1] = client
        return client

    async def aclose(self) -> None:
        """Close every pooled client (call on application shutdown)."""
        for client in self._clients.values():
            if not client.is_closed:
                await client.aclose()
        self._clients.clear()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
        timeout: Optional[float] = None,
        error_label: str = "ML Engine",
        include_headers: bool = True,
    ) -> Any:
        client = self._get_client()
        request_headers = self._headers if include_headers else None

        retryable_statuses = {429, 502, 503, 504}
        last_error: Optional[Exception] = None
        for attempt in range(self._retries + 1):
            try:
                resp = await client.request(
                    method,
                    f"{self._base_url}{path}",
                    json=json,
                    params=params,
                    headers=request_headers,
                    timeout=timeout,
                )
                if resp.status_code in retryable_statuses and attempt < self._retries:
                    backoff = _backoff_with_jitter(self._retry_backoff, attempt)
                    logger.info(
                        "%s returned %s (attempt %d/%d); retrying in %.2fs",
                        error_label, resp.status_code, attempt + 1, self._retries + 1, backoff,
                    )
                    await asyncio.sleep(backoff)
                    continue
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status in retryable_statuses and attempt < self._retries:
                    backoff = _backoff_with_jitter(self._retry_backoff, attempt)
                    await asyncio.sleep(backoff)
                    continue
                logger.error(
                    "%s failed: %s %s", error_label, status, e.response.text
                )
                raise MLEngineClientError(
                    f"ML Engine returned {status}: {e.response.text}",
                    status_code=status,
                ) from e
            except httpx.RequestError as e:
                last_error = e
                if attempt >= self._retries:
                    break
                backoff = _backoff_with_jitter(self._retry_backoff, attempt)
                logger.info(
                    "%s request failed (attempt %d/%d): %s; retrying in %.2fs",
                    error_label, attempt + 1, self._retries + 1, str(e), backoff,
                )
                await asyncio.sleep(backoff)

        raise MLEngineClientError(
            f"ML Engine request failed: {last_error}", status_code=None
        ) from last_error

    async def execute_unlearning(
        self,
        target_data_ids: list[str],
        model_type: str = "transformer",
        model_name: str = "",
        data_size: int = 0,
        latency_ms: int = 500,
        accuracy_target: float = 0.95,
        regulatory: str = "gdpr",
        config: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "target_data_ids": target_data_ids,
            "model_type": model_type,
            "model_name": model_name,
            "data_size": data_size,
            "latency_ms": latency_ms,
            "accuracy_target": accuracy_target,
            "regulatory": regulatory,
            "config": config or {},
        }
        return await self._request("POST", "/unlearn", json=payload, error_label="ML Engine unlearning")

    async def generate_proof(
        self,
        deletion_steps: list[str],
        algorithm: str = "ed25519",
    ) -> dict[str, Any]:
        payload = {
            "deletion_steps": deletion_steps,
            "algorithm": algorithm,
        }
        return await self._request("POST", "/proof/generate", json=payload, error_label="ML Engine proof generation")

    async def verify_proof(
        self,
        message: str,
        signature_hex: str,
        public_key_pem: str,
    ) -> dict[str, Any]:
        payload = {
            "message": message,
            "signature_hex": signature_hex,
            "public_key_pem": public_key_pem,
        }
        return await self._request("POST", "/proof/verify", json=payload, error_label="ML Engine proof verification")

    async def generate_certificate(
        self,
        target_data_ids: list[str],
        model_name: str = "",
        data_size: int = 0,
        regulatory: str = "gdpr",
        config: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        payload = {
            "target_data_ids": target_data_ids,
            "model_name": model_name,
            "data_size": data_size,
            "regulatory": regulatory,
            "config": config or {},
        }
        return await self._request("POST", "/certificate", json=payload, error_label="ML Engine certificate generation")

    async def evaluate_privacy(
        self,
        target_data_ids: list[str],
        model_name: str = "",
        data_size: int = 0,
        config: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        payload = {
            "target_data_ids": target_data_ids,
            "model_name": model_name,
            "data_size": data_size,
            "config": config or {},
        }
        return await self._request("POST", "/evaluate/privacy", json=payload, error_label="ML Engine privacy evaluation")

    async def evaluate_mia(
        self,
        target_data_ids: list[str],
        model_name: str = "",
        data_size: int = 0,
        config: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        payload = {
            "target_data_ids": target_data_ids,
            "model_name": model_name,
            "data_size": data_size,
            "config": config or {},
        }
        return await self._request("POST", "/evaluate/mia", json=payload, error_label="ML Engine MIA evaluation")

    async def generate_zksnark_proof(
        self,
        leaf_data: str,
        all_leaves: list[str],
        hash_algorithm: str = "sha3_256",
    ) -> dict[str, Any]:
        payload = {
            "leaf_data": leaf_data,
            "all_leaves": all_leaves,
            "hash_algorithm": hash_algorithm,
        }
        return await self._request("POST", "/proof/generate-zksnark", json=payload, error_label="ML Engine zk-SNARK proof gen")

    async def verify_zksnark_proof(
        self,
        proof_dict: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {"proof": proof_dict}
        return await self._request("POST", "/proof/verify-zksnark", json=payload, error_label="ML Engine zk-SNARK verify")

    async def generate_text(
        self,
        prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        stream: bool = False,
        adapter_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "prompt": prompt,
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "stream": stream,
        }
        if adapter_name:
            payload["adapter_name"] = adapter_name
        if system_prompt:
            payload["system_prompt"] = system_prompt
        return await self._request("POST", "/inference/generate", json=payload, error_label="ML Engine text generation")

    async def generate_text_stream(
        self,
        prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        adapter_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        payload: dict[str, Any] = {
            "prompt": prompt,
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "stream": True,
        }
        if adapter_name:
            payload["adapter_name"] = adapter_name
        if system_prompt:
            payload["system_prompt"] = system_prompt
        client = self._get_client()
        try:
            async with client.stream(
                "POST",
                f"{self._base_url}/inference/generate/stream",
                json=payload,
                headers=self._headers,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        yield data
        except httpx.HTTPStatusError as e:
            logger.error("ML Engine streaming failed: %s %s", e.response.status_code, e.response.text)
            raise MLEngineClientError(
                f"ML Engine returned {e.response.status_code}: {e.response.text}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            logger.error("ML Engine stream request failed: %s", str(e))
            raise MLEngineClientError(f"ML Engine request failed: {e}", status_code=None) from e

    async def ingest_document(
        self,
        text: str,
        source_name: str,
        metadata: dict[str, Any] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "text": text,
            "source_name": source_name,
            "metadata": metadata or {},
        }
        return await self._request("POST", "/rag/documents/ingest-text", json=payload, error_label="ML Engine document ingestion")

    async def search_documents(
        self,
        query: str,
        top_k: int = 5,
        filters: dict[str, Any] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "query": query,
            "top_k": top_k,
            "filters": filters or {},
        }
        return await self._request("POST", "/rag/search", json=payload, error_label="ML Engine RAG search")

    async def process_document(
        self,
        document_id: str,
        filename: str,
        file_type: str,
        storage_path: str = "",
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "document_id": document_id,
            "filename": filename,
            "file_type": file_type,
            "storage_path": storage_path,
        }
        return await self._request("POST", "/rag/documents/process", json=payload, error_label="ML Engine document processing")

    async def generate_embeddings(
        self,
        document_id: str,
        chunk_count: int = 0,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "document_id": document_id,
            "chunk_count": chunk_count,
        }
        return await self._request("POST", "/rag/embeddings/generate", json=payload, error_label="ML Engine embedding generation")

    async def ocr_process(
        self,
        document_id: str,
        storage_path: str,
        file_type: str,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "document_id": document_id,
            "storage_path": storage_path,
            "file_type": file_type,
        }
        return await self._request("POST", "/rag/documents/ocr", json=payload, error_label="ML Engine OCR processing")

    async def record_conversation(
        self,
        user_id: str,
        tenant_id: str,
        turns: list[dict[str, Any]],
        feedback: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "turns": turns,
        }
        if feedback:
            payload["feedback"] = feedback
        return await self._request("POST", "/conversations/record", json=payload, error_label="ML Engine conversation record")

    async def execute_e2e_unlearning(
        self,
        tenant_id: str,
        user_id: str,
        target_data_ids: list[str],
        model_name: str,
        reason: str,
        regulatory: str,
        priority: str,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "target_data_ids": target_data_ids,
            "model_name": model_name,
            "reason": reason,
            "regulatory": regulatory,
            "priority": priority,
        }
        return await self._request("POST", "/unlearn/e2e", json=payload, error_label="ML Engine E2E unlearning")

    async def train_lora(
        self,
        conversations: list[dict[str, Any]],
        model_name: str,
        lora_r: int = 16,
        lora_alpha: int = 32,
        num_epochs: int = 3,
        batch_size: int = 8,
        learning_rate: float = 1e-4,
        remove_data_ids: list[str] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "conversations": conversations,
            "model_name": model_name,
            "lora_r": lora_r,
            "lora_alpha": lora_alpha,
            "num_epochs": num_epochs,
            "batch_size": batch_size,
            "learning_rate": learning_rate,
            "remove_data_ids": remove_data_ids or [],
        }
        return await self._request("POST", "/train/lora", json=payload, error_label="ML Engine LoRA training")

    async def explain_samples(
        self,
        samples: list[list[float]],
        feature_names: Optional[list[str]] = None,
        method: str = "shap",
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "samples": samples,
            "method": method,
        }
        if feature_names:
            payload["feature_names"] = feature_names
        return await self._request("POST", "/explain/samples", json=payload, error_label="ML Engine explain samples")

    async def explain_features(
        self,
        dataset: list[list[float]],
        feature_names: Optional[list[str]] = None,
        method: str = "shap",
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "dataset": dataset,
            "method": method,
        }
        if feature_names:
            payload["feature_names"] = feature_names
        return await self._request("POST", "/explain/features", json=payload, error_label="ML Engine explain features")

    async def compare_explanations(
        self,
        pre_unlearn_samples: list[list[float]],
        post_unlearn_samples: list[list[float]],
        feature_names: Optional[list[str]] = None,
        method: str = "shap",
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "pre_unlearn_samples": pre_unlearn_samples,
            "post_unlearn_samples": post_unlearn_samples,
            "method": method,
        }
        if feature_names:
            payload["feature_names"] = feature_names
        return await self._request("POST", "/explain/compare", json=payload, error_label="ML Engine compare explanations")

    async def privacy_heatmap(
        self,
        samples: list[list[float]],
        privacy_scores: list[float],
        feature_names: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "samples": samples,
            "privacy_scores": privacy_scores,
        }
        if feature_names:
            payload["feature_names"] = feature_names
        return await self._request("POST", "/explain/privacy-heatmap", json=payload, error_label="ML Engine privacy heatmap")

    async def model_drift(
        self,
        pre_confidences: list[float],
        post_confidences: list[float],
        pre_importances: list[dict[str, float]],
        post_importances: list[dict[str, float]],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "pre_confidences": pre_confidences,
            "post_confidences": post_confidences,
            "pre_importances": pre_importances,
            "post_importances": post_importances,
        }
        return await self._request("POST", "/explain/drift", json=payload, error_label="ML Engine model drift")

    async def list_explain_methods(self) -> dict[str, Any]:
        return await self._request("GET", "/explain/methods", timeout=10, error_label="ML Engine explain methods")

    async def register_adapter(
        self,
        adapter_name: str,
        adapter_path: str,
        base_model_name: str = "",
        config: Optional[dict[str, Any]] = None,
        tags: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "adapter_name": adapter_name,
            "adapter_path": adapter_path,
            "base_model_name": base_model_name,
            "config": config or {},
            "tags": tags or {},
        }
        return await self._request("POST", "/adapters/register", json=payload, error_label="ML Engine adapter register")

    async def list_adapters(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/adapters", timeout=10, error_label="ML Engine list adapters")

    async def activate_adapter(self, adapter_name: str, version_id: str) -> dict[str, Any]:
        payload = {"adapter_name": adapter_name, "version_id": version_id}
        return await self._request("POST", "/adapters/activate", json=payload, error_label="ML Engine adapter activate")

    async def rollback_adapter(self, adapter_name: str, version_id: Optional[str] = None) -> dict[str, Any]:
        params = {}
        if version_id:
            params["version_id"] = version_id
        return await self._request(
            "POST", f"/adapters/{adapter_name}/rollback", params=params, error_label="ML Engine adapter rollback"
        )

    async def get_adapter_versions(self, adapter_name: str) -> list[dict[str, Any]]:
        return await self._request(
            "GET", f"/adapters/{adapter_name}/versions", timeout=10, error_label="ML Engine adapter versions"
        )

    async def get_adapter_health(self, adapter_name: str) -> dict[str, Any]:
        return await self._request(
            "GET", f"/adapters/{adapter_name}/health", timeout=10, error_label="ML Engine adapter health"
        )

    async def setup_canary(
        self,
        adapter_name: str,
        stable_version_id: str,
        canary_version_id: str,
        canary_traffic_pct: Optional[float] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "adapter_name": adapter_name,
            "stable_version_id": stable_version_id,
            "canary_version_id": canary_version_id,
        }
        if canary_traffic_pct is not None:
            payload["canary_traffic_pct"] = canary_traffic_pct
        return await self._request("POST", "/adapters/canary/setup", json=payload, error_label="ML Engine canary setup")

    async def deactivate_adapter(self, adapter_name: str, version_id: str) -> dict[str, Any]:
        payload = {"adapter_name": adapter_name, "version_id": version_id}
        return await self._request("POST", "/adapters/deactivate", json=payload, error_label="ML Engine adapter deactivate")

    async def get_active_adapter(self, adapter_name: str) -> dict[str, Any]:
        return await self._request(
            "GET", f"/adapters/{adapter_name}/active", timeout=10, error_label="ML Engine active adapter"
        )

    async def record_adapter_metrics(
        self, adapter_name: str, version_id: str, latency_ms: float, success: bool = True
    ) -> dict[str, Any]:
        payload = {"adapter_name": adapter_name, "version_id": version_id, "latency_ms": latency_ms, "success": success}
        return await self._request("POST", "/adapters/metrics", json=payload, error_label="ML Engine adapter metrics")

    async def get_adapter_latency_stats(self, adapter_name: str) -> dict[str, Any]:
        return await self._request(
            "GET", f"/adapters/{adapter_name}/latency", timeout=10, error_label="ML Engine adapter latency"
        )

    async def run_benchmarks(self, config: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        payload = config or {}
        return await self._request("POST", "/benchmarks/run", json=payload, timeout=600, error_label="ML Engine benchmarks run")

    async def get_benchmark_summary(self) -> dict[str, Any]:
        return await self._request("GET", "/benchmarks/summary", timeout=30, error_label="ML Engine benchmark summary")

    async def get_continual_stats(self) -> dict[str, Any]:
        return await self._request("GET", "/continual/stats", timeout=10, error_label="ML Engine continual stats")

    async def record_continual_sample(self, sample: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/continual/samples", json=sample, error_label="ML Engine continual sample")

    async def get_continual_drift_alerts(self, n: int = 10) -> dict[str, Any]:
        return await self._request(
            "GET", f"/continual/drift/alerts?n={n}", timeout=10, error_label="ML Engine drift alerts"
        )

    async def promote_canary(self, adapter_name: str) -> dict[str, Any]:
        return await self._request(
            "POST", f"/adapters/{adapter_name}/canary/promote", error_label="ML Engine canary promote"
        )

    async def run_model_inversion(
        self,
        target_classes: list[int],
        input_dim: int = 20,
        num_samples: int = 1,
        iterations: int = 500,
        learning_rate: float = 0.1,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "target_classes": target_classes,
            "input_dim": input_dim,
            "num_samples": num_samples,
            "iterations": iterations,
            "learning_rate": learning_rate,
        }
        return await self._request("POST", "/attacks/model-inversion", json=payload, error_label="ML Engine model inversion")

    async def run_shadow_mia(
        self,
        num_shadow_models: int = 5,
        shadow_data_size: int = 200,
        shadow_epochs: int = 50,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "num_shadow_models": num_shadow_models,
            "shadow_data_size": shadow_data_size,
            "shadow_epochs": shadow_epochs,
        }
        return await self._request("POST", "/attacks/shadow-mia", json=payload, error_label="ML Engine shadow MIA")

    async def run_model_extraction(
        self,
        input_dim: int = 20,
        num_classes: int = 2,
        num_queries: int = 1000,
        extraction_epochs: int = 200,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "input_dim": input_dim,
            "num_classes": num_classes,
            "num_queries": num_queries,
            "extraction_epochs": extraction_epochs,
        }
        return await self._request("POST", "/attacks/model-extraction", json=payload, error_label="ML Engine model extraction")

    async def get_attack_methods(self) -> dict[str, Any]:
        return await self._request("GET", "/attacks/methods", timeout=10, error_label="ML Engine attack methods")

    async def run_hpo(
        self,
        n_trials: int = 10,
        direction: str = "maximize",
        param_space: Optional[dict[str, Any]] = None,
        study_name: Optional[str] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"n_trials": n_trials, "direction": direction}
        if param_space:
            payload["param_space"] = param_space
        if study_name:
            payload["study_name"] = study_name
        return await self._request("POST", "/hpo/optimize", json=payload, timeout=600, error_label="ML Engine HPO")

    async def export_model(
        self,
        export_format: str = "onnx",
        model_name: str = "model",
        input_dim: int = 20,
        num_classes: int = 2,
        fp16: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "format": export_format,
            "model_name": model_name,
            "input_dim": input_dim,
            "num_classes": num_classes,
            "fp16": fp16,
        }
        return await self._request("POST", "/model/export", json=payload, error_label="ML Engine model export")

    async def get_controller_health(self) -> dict[str, Any]:
        return await self._request("GET", "/controller/health", timeout=10, error_label="ML Engine controller health")

    async def get_registry_stats(self) -> dict[str, Any]:
        return await self._request("GET", "/registry/stats", timeout=10, error_label="ML Engine registry stats")

    async def health(self) -> dict[str, Any]:
        client = self._get_client()
        try:
            resp = await client.get(f"{self._base_url}/health", timeout=10)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.error("ML Engine health check failed: %s", str(e))
            status_code = getattr(getattr(e, "response", None), "status_code", None)
            raise MLEngineClientError(
                f"ML Engine health check failed: {e}", status_code=status_code
            ) from e

    async def delete_document(self, document_id: str) -> dict[str, Any]:
        return await self._request(
            "DELETE", f"/rag/documents/{document_id}", error_label="ML Engine document delete"
        )

    async def upsert_embedding(
        self, collection: str, point_id: str, vector: list[float], payload: dict[str, Any]
    ) -> None:
        await self._request(
            "POST",
            "/rag/vectors/upsert",
            json={
                "collection": collection,
                "point_id": point_id,
                "vector": vector,
                "payload": payload or {},
            },
            error_label="ML Engine embedding upsert",
        )

    async def delete_vectors(self, collection: str, filter_: dict[str, Any]) -> None:
        await self._request(
            "POST",
            "/rag/vectors/delete",
            json={"collection": collection, "filter": filter_ or {}},
            error_label="ML Engine vector delete",
        )

    # Provider hostnames that are safe to send credentials to. Probes against
    # any other host run without an API key, and private/link-local targets are
    # rejected outright (SSRF guard). Azure endpoints are per-resource and must
    # be configured explicitly via base_url.
    _PROVIDER_ALLOWLIST_HOSTS = {
        "api.openai.com",
        "api.anthropic.com",
        "generativelanguage.googleapis.com",
    }

    async def test_provider(
        self, provider_type: str, config: dict[str, Any], api_key: Optional[str]
    ) -> dict[str, Any]:
        """Probe a provider endpoint for reachability with a short, bounded request.

        Security (SSRF guard):
        * The probe target is restricted to HTTP(S) URLs.
        * Hosts resolving to private / loopback / link-local / reserved IPs are
          rejected so an authenticated caller cannot make the backend scan
          internal networks or reach cloud metadata endpoints.
        * The API key is only attached for allowlisted provider hostnames;
          probes against any other host run without credentials.
        * Any connection error, timeout, or non-2xx response is reported as
          unreachable (fails closed).
        """
        from urllib.parse import urlparse

        base_url = (config or {}).get("base_url", "")
        default_urls = {
            "openai": "https://api.openai.com/v1",
            "anthropic": "https://api.anthropic.com/v1",
            "google": "https://generativelanguage.googleapis.com/v1beta",
        }
        base_url = base_url or default_urls.get(provider_type, "")

        if not base_url:
            return {
                "provider_type": provider_type,
                "reachable": False,
                "message": (
                    "Provider has no base_url configured and no default exists; "
                    "set one in the provider config to test connectivity"
                ),
            }

        parsed = urlparse(base_url)
        if parsed.scheme not in ("http", "https"):
            return {
                "provider_type": provider_type,
                "reachable": False,
                "message": "Provider base_url must be http(s) — refusing to probe other schemes",
            }
        host = parsed.hostname or ""

        # SSRF guard: reject targets that resolve to non-public address space.
        if not self._host_is_public(host):
            return {
                "provider_type": provider_type,
                "reachable": False,
                "message": f"Provider host '{host}' resolves to a non-public address — probe blocked",
            }

        probe_url = base_url.rstrip("/")
        headers: dict[str, str] = {"Content-Type": "application/json"}
        allow_credentials = host in self._PROVIDER_ALLOWLIST_HOSTS
        if api_key and allow_credentials:
            if provider_type == "anthropic":
                headers["x-api-key"] = api_key
                headers["anthropic-version"] = "2023-06-01"
            else:
                headers["Authorization"] = f"Bearer {api_key}"

        try:
            client = self._get_client()
            resp = await client.get(probe_url, headers=headers, timeout=10)
            reachable = resp.status_code < 500
            return {
                "provider_type": provider_type,
                "reachable": reachable,
                "status_code": resp.status_code,
                "credentials_sent": allow_credentials and bool(api_key),
                "message": (
                    f"Provider responded with HTTP {resp.status_code}"
                    if reachable
                    else f"Provider returned HTTP {resp.status_code} (server-side error)"
                ),
            }
        except httpx.RequestError as e:
            logger.warning("Provider reachability check failed for %s: %s", provider_type, str(e))
            return {
                "provider_type": provider_type,
                "reachable": False,
                "message": f"Provider unreachable: {e.__class__.__name__}",
            }

    @staticmethod
    def _host_is_public(host: str) -> bool:
        """True only if every resolved address of ``host`` is globally routable."""
        import ipaddress
        import socket

        if not host:
            return False
        try:
            infos = socket.getaddrinfo(host, None)
        except socket.gaierror:
            return False
        if not infos:
            return False
        for info in infos:
            try:
                ip = ipaddress.ip_address(info[4][0])
            except ValueError:
                continue
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
                or ip.is_unspecified
            ):
                return False
        return True


ml_engine_client = MLEngineClient(
    base_url=settings.ml_engine_url,
    api_key=settings.ml_engine_api_key,
    timeout=settings.ml_request_timeout,
)
