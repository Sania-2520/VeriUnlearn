"""Adapter lifecycle management endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException

from api import deps
from api.schemas import (
    AdapterVersionActionRequest,
    CanarySetupRequest,
    RecordMetricsRequest,
    RegisterAdapterRequest,
)

router = APIRouter()


class AdapterLifecycleRouter:
    """Thin HTTP-facing facade over :class:`AdapterLifecycleManager`.

    Kept as a class (rather than inlined into handlers) to preserve the
    historical public shape of the router while keeping each handler small.
    """

    def __init__(self) -> None:
        self._manager = deps.get_adapter_lifecycle()

    def register(self, request: RegisterAdapterRequest) -> dict:
        version = self._manager.register_adapter(
            adapter_name=request.adapter_name,
            adapter_path=request.adapter_path,
            base_model_name=request.base_model_name,
            config=request.config,
            tags=request.tags,
        )
        return {
            "adapter_name": version.adapter_name,
            "version_id": version.version_id,
            "version_number": version.version_number,
            "status": version.status.value,
        }

    def activate(self, request: AdapterVersionActionRequest) -> dict:
        success = self._manager.activate_version(request.adapter_name, request.version_id)
        return {"success": success}

    def deactivate(self, request: AdapterVersionActionRequest) -> dict:
        success = self._manager.deactivate_version(request.adapter_name, request.version_id)
        return {"success": success}

    def mark_failed(self, request: AdapterVersionActionRequest) -> dict:
        success = self._manager.mark_failed(request.adapter_name, request.version_id)
        return {"success": success}

    def rollback(self, adapter_name: str, version_id: Optional[str] = None) -> dict:
        target = self._manager.rollback(adapter_name, version_id)
        if target is None:
            raise HTTPException(status_code=404, detail=f"No rollback target for '{adapter_name}'")
        return {
            "adapter_name": target.adapter_name,
            "version_id": target.version_id,
            "version_number": target.version_number,
            "status": target.status.value,
        }

    def list_adapters(self) -> list[dict]:
        return self._manager.list_adapters()

    def get_versions(self, adapter_name: str) -> list[dict]:
        return self._manager.get_versions(adapter_name)

    def get_active(self, adapter_name: str) -> dict:
        version = self._manager.get_active_version(adapter_name)
        if version is None:
            raise HTTPException(status_code=404, detail=f"No active version for '{adapter_name}'")
        return {
            "adapter_name": version.adapter_name,
            "version_id": version.version_id,
            "version_number": version.version_number,
            "status": version.status.value,
            "avg_latency_ms": version.avg_latency_ms,
            "total_requests": version.total_requests,
        }

    def setup_canary(self, request: CanarySetupRequest) -> dict:
        self._manager.setup_canary(
            request.adapter_name,
            request.stable_version_id,
            request.canary_version_id,
            request.canary_traffic_pct,
        )
        return {"success": True, "strategy": "canary"}

    def promote_canary(self, adapter_name: str) -> dict:
        version = self._manager.promote_canary(adapter_name)
        if version is None:
            raise HTTPException(status_code=400, detail=f"No canary deployment for '{adapter_name}'")
        return {
            "adapter_name": version.adapter_name,
            "version_id": version.version_id,
            "version_number": version.version_number,
            "status": version.status.value,
        }

    def get_routing(self, adapter_name: str) -> dict:
        rule = self._manager.get_routing_rule(adapter_name)
        if rule is None:
            raise HTTPException(status_code=404, detail=f"No routing rule for '{adapter_name}'")
        return rule

    def record_metrics(self, request: RecordMetricsRequest) -> dict:
        self._manager.record_request(
            request.adapter_name, request.version_id, request.latency_ms, request.success
        )
        return {"success": True}

    def get_latency(self, adapter_name: str) -> dict:
        return self._manager.get_latency_stats(adapter_name)

    def health(self, adapter_name: str) -> dict:
        return self._manager.get_adapter_health(adapter_name)


_lifecycle_router: Optional[AdapterLifecycleRouter] = None


def get_lifecycle_router() -> AdapterLifecycleRouter:
    global _lifecycle_router
    if _lifecycle_router is None:
        _lifecycle_router = AdapterLifecycleRouter()
    return _lifecycle_router


@router.post("/adapters/register")
async def register_adapter(request: RegisterAdapterRequest):
    return get_lifecycle_router().register(request)


@router.post("/adapters/activate")
async def activate_adapter(request: AdapterVersionActionRequest):
    return get_lifecycle_router().activate(request)


@router.post("/adapters/deactivate")
async def deactivate_adapter(request: AdapterVersionActionRequest):
    return get_lifecycle_router().deactivate(request)


@router.post("/adapters/mark-failed")
async def mark_adapter_failed(request: AdapterVersionActionRequest):
    return get_lifecycle_router().mark_failed(request)


@router.post("/adapters/{adapter_name}/rollback")
async def rollback_adapter(adapter_name: str, version_id: Optional[str] = None):
    return get_lifecycle_router().rollback(adapter_name, version_id)


@router.get("/adapters")
async def list_adapters():
    return get_lifecycle_router().list_adapters()


@router.get("/adapters/{adapter_name}/versions")
async def get_adapter_versions(adapter_name: str):
    return get_lifecycle_router().get_versions(adapter_name)


@router.get("/adapters/{adapter_name}/active")
async def get_active_adapter(adapter_name: str):
    return get_lifecycle_router().get_active(adapter_name)


@router.post("/adapters/canary/setup")
async def setup_canary(request: CanarySetupRequest):
    return get_lifecycle_router().setup_canary(request)


@router.post("/adapters/{adapter_name}/canary/promote")
async def promote_canary(adapter_name: str):
    return get_lifecycle_router().promote_canary(adapter_name)


@router.get("/adapters/{adapter_name}/routing")
async def get_routing_rule(adapter_name: str):
    return get_lifecycle_router().get_routing(adapter_name)


@router.post("/adapters/metrics")
async def record_adapter_metrics(request: RecordMetricsRequest):
    return get_lifecycle_router().record_metrics(request)


@router.get("/adapters/{adapter_name}/latency")
async def get_adapter_latency(adapter_name: str):
    return get_lifecycle_router().get_latency(adapter_name)


@router.get("/adapters/{adapter_name}/health")
async def adapter_health(adapter_name: str):
    return get_lifecycle_router().health(adapter_name)
