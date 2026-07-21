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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/rag/documents/process",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine document processing failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine document processing request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

    async def generate_embeddings(
        self,
        document_id: str,
        chunk_count: int = 0,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "document_id": document_id,
            "chunk_count": chunk_count,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/rag/embeddings/generate",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine embedding generation failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine embedding generation request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/rag/documents/ocr",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine OCR processing failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine OCR processing request failed: %s", str(e))
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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/explain/samples",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine explain samples failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine explain samples request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/explain/features",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine explain features failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine explain features request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/explain/compare",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine compare explanations failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine compare explanations request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/explain/privacy-heatmap",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine privacy heatmap failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine privacy heatmap request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/explain/drift",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine model drift failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine model drift request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

    async def list_explain_methods(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(
                    f"{self._base_url}/explain/methods",
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine explain methods failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine explain methods request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(f"{self._base_url}/adapters/register", json=payload, headers=self._headers)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine adapter register failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine adapter register request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

    async def list_adapters(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(f"{self._base_url}/adapters", headers=self._headers)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine list adapters failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine list adapters request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

    async def activate_adapter(self, adapter_name: str, version_id: str) -> dict[str, Any]:
        payload = {"adapter_name": adapter_name, "version_id": version_id}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(f"{self._base_url}/adapters/activate", json=payload, headers=self._headers)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine adapter activate failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine adapter activate request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

    async def rollback_adapter(self, adapter_name: str, version_id: Optional[str] = None) -> dict[str, Any]:
        params = {}
        if version_id:
            params["version_id"] = version_id
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/adapters/{adapter_name}/rollback",
                    params=params,
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine adapter rollback failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine adapter rollback request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

    async def get_adapter_versions(self, adapter_name: str) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(f"{self._base_url}/adapters/{adapter_name}/versions", headers=self._headers)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine adapter versions failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine adapter versions request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

    async def get_adapter_health(self, adapter_name: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(f"{self._base_url}/adapters/{adapter_name}/health", headers=self._headers)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine adapter health failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine adapter health request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(f"{self._base_url}/adapters/canary/setup", json=payload, headers=self._headers)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine canary setup failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine canary setup request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

    async def deactivate_adapter(self, adapter_name: str, version_id: str) -> dict[str, Any]:
        payload = {"adapter_name": adapter_name, "version_id": version_id}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(f"{self._base_url}/adapters/deactivate", json=payload, headers=self._headers)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine adapter deactivate failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine adapter deactivate request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

    async def get_active_adapter(self, adapter_name: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(f"{self._base_url}/adapters/{adapter_name}/active", headers=self._headers)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine active adapter failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine active adapter request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

    async def record_adapter_metrics(
        self, adapter_name: str, version_id: str, latency_ms: float, success: bool = True
    ) -> dict[str, Any]:
        payload = {"adapter_name": adapter_name, "version_id": version_id, "latency_ms": latency_ms, "success": success}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(f"{self._base_url}/adapters/metrics", json=payload, headers=self._headers)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine adapter metrics failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine adapter metrics request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

    async def get_adapter_latency_stats(self, adapter_name: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(f"{self._base_url}/adapters/{adapter_name}/latency", headers=self._headers)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine adapter latency failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine adapter latency request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

    async def run_benchmarks(self, config: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        payload = config or {}
        async with httpx.AsyncClient(timeout=600) as client:
            try:
                resp = await client.post(f"{self._base_url}/benchmarks/run", json=payload, headers=self._headers)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine benchmarks run failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine benchmarks request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

    async def get_benchmark_summary(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.get(f"{self._base_url}/benchmarks/summary", headers=self._headers)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine benchmark summary failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine benchmark summary request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

    async def get_continual_stats(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(f"{self._base_url}/continual/stats", headers=self._headers)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine continual stats failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine continual stats request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

    async def record_continual_sample(self, sample: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(f"{self._base_url}/continual/samples", json=sample, headers=self._headers)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine continual sample failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine continual sample request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

    async def get_continual_drift_alerts(self, n: int = 10) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(f"{self._base_url}/continual/drift/alerts?n={n}", headers=self._headers)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine drift alerts failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine drift alerts request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

    async def promote_canary(self, adapter_name: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(f"{self._base_url}/adapters/{adapter_name}/canary/promote", headers=self._headers)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine canary promote failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine canary promote request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/attacks/model-inversion",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine model inversion failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine model inversion request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/attacks/shadow-mia",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine shadow MIA failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine shadow MIA request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/attacks/model-extraction",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine model extraction failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine model extraction request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

    async def get_attack_methods(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(
                    f"{self._base_url}/attacks/methods",
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine attack methods failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine attack methods request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

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
        async with httpx.AsyncClient(timeout=600) as client:
            try:
                resp = await client.post(f"{self._base_url}/hpo/optimize", json=payload, headers=self._headers)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine HPO failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine HPO request failed: %s", str(e))
                raise MLEngineClientError(f"ML Engine request failed: {e}")

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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.post(f"{self._base_url}/model/export", json=payload, headers=self._headers)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("ML Engine model export failed: %s %s", e.response.status_code, e.response.text)
                raise MLEngineClientError(f"ML Engine returned {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error("ML Engine model export request failed: %s", str(e))
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
