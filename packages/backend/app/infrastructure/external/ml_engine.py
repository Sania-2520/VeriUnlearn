from typing import Any, Optional

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
