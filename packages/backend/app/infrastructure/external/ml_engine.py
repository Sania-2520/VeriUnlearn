from typing import Any, AsyncGenerator, Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class MLEngineClientError(Exception):
    pass


class MLEngineClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: int = 300) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            self._headers["X-API-Key"] = api_key

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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/unlearn",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine unlearning failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

    async def generate_proof(
        self,
        deletion_steps: list[str],
        algorithm: str = "ed25519",
    ) -> dict[str, Any]:
        payload = {
            "deletion_steps": deletion_steps,
            "algorithm": algorithm,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/proof/generate",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine proof generation failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine proof request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/proof/verify",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine proof verification failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine verify request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/certificate",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine certificate generation failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine certificate request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/evaluate/privacy",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine privacy evaluation failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine privacy request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/evaluate/mia",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine MIA evaluation failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine MIA request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/proof/generate-zksnark",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine zk-SNARK proof gen failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine zk-SNARK request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

    async def verify_zksnark_proof(
        self,
        proof_dict: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {"proof": proof_dict}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/proof/verify-zksnark",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine zk-SNARK verify failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine zk-SNARK verify request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/inference/generate",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine text generation failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine generation request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
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
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine stream request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/rag/documents/ingest-text",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine document ingestion failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine ingestion request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/rag/search",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine RAG search failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine RAG search request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/conversations/record",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine conversation record failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine conversation record request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/unlearn/e2e",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine E2E unlearning failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine E2E unlearning request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

    async def train_lora(
        self,
        conversations: list[dict[str, Any]],
        model_name: str,
        lora_r: int = 16,
        num_epochs: int = 3,
        batch_size: int = 8,
        learning_rate: float = 1e-4,
        remove_data_ids: list[str] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "conversations": conversations,
            "model_name": model_name,
            "lora_r": lora_r,
            "num_epochs": num_epochs,
            "batch_size": batch_size,
            "learning_rate": learning_rate,
            "remove_data_ids": remove_data_ids or [],
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/train/lora",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine LoRA training failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine LoRA training request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

    async def get_controller_health(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(
                    f"{self._base_url}/controller/health",
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine controller health failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine controller health request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

    async def get_registry_stats(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(
                    f"{self._base_url}/registry/stats",
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine registry stats failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine registry stats request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

    async def health(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(f"{self._base_url}/health")
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPError as e:
                logger.error("ML Engine health check failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine health check failed: {e}")


ml_engine_client = MLEngineClient(
    base_url=settings.ml_engine_url,
    api_key=settings.ml_engine_api_key,
    timeout=settings.ml_request_timeout,
)
