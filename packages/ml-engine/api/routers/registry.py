"""Model registry and model export endpoints."""

from fastapi import APIRouter, HTTPException

from api import deps
from api.schemas import ModelExportRequest, ModelRegistryRequest

router = APIRouter()


@router.post("/registry/versions")
async def register_model_version(request: ModelRegistryRequest):
    registry = deps.get_model_registry()
    result = registry.register_version(
        model_name=request.model_name,
        checkpoint_path=request.checkpoint_path,
        algorithm=request.algorithm,
        parent_version_id=request.parent_version_id,
        config=request.config,
        metrics=request.metrics,
    )
    return result


@router.get("/registry/versions")
async def list_all_versions():
    registry = deps.get_model_registry()
    return registry.list_versions()


@router.get("/registry/versions/{model_name}")
async def list_model_versions(model_name: str):
    registry = deps.get_model_registry()
    return registry.list_versions(model_name=model_name)


@router.get("/registry/versions/{model_name}/{version_id}")
async def get_model_version(model_name: str, version_id: str):
    registry = deps.get_model_registry()
    version = registry.get_version(model_name, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail=f"Version {version_id} not found for model {model_name}")
    return version


@router.post("/registry/versions/{model_name}/{version_id}/rollback")
async def rollback_model_version(model_name: str, version_id: str):
    registry = deps.get_model_registry()
    result = registry.rollback(model_name, version_id)
    return result


@router.post("/registry/versions/{model_name}/{version_id}/verify")
async def verify_model_version(model_name: str, version_id: str):
    registry = deps.get_model_registry()
    result = registry.verify_integrity(model_name, version_id)
    return result


@router.get("/registry/stats")
async def registry_stats():
    registry = deps.get_model_registry()
    return registry.get_stats()


@router.post("/model/register")
async def register_model(request: ModelRegistryRequest):
    registry = deps.get_model_registry()
    version = registry.register_version(
        model_name=request.model_name,
        checkpoint_path=request.checkpoint_path,
        algorithm=request.algorithm,
        parent_version_id=request.parent_version_id,
        config=request.config,
        metrics=request.metrics,
    )
    return {
        "version_id": version.version_id,
        "model_name": version.model_name,
        "version_number": version.version_number,
        "status": version.status,
    }


@router.get("/model/versions")
async def list_all_model_versions(model_name: str = "", limit: int = 50):
    registry = deps.get_model_registry()
    if model_name:
        versions = registry.get_model_versions(model_name)
    else:
        versions = registry.list_all()
    return versions[:limit]


@router.post("/model/export")
async def export_model(request: ModelExportRequest):
    from inference.model_export import ModelExportService
    from unlearning.algorithms.base import UnlearningContext
    from unlearning.algorithms.sisa import SISAUnlearning

    ctx = UnlearningContext(
        target_data_ids=["data_000000"],
        model_name="export_target",
        data_size=200,
    )
    algo = SISAUnlearning(num_shards=4)
    await algo.unlearn(ctx)

    service = ModelExportService()
    fmt = request.format.lower()
    if fmt in ("tensorrt", "trt"):
        result = service.export_tensorrt(algo.model, request.model_name, fp16=request.fp16)
    elif fmt in ("openvino", "ov"):
        result = service.export_openvino(algo.model, request.model_name, fp16=request.fp16)
    else:
        result = service.export_onnx(algo.model, request.model_name)

    return {
        "format": result.format,
        "export_path": result.export_path,
        "success": result.success,
        "error": result.error,
        "metadata": result.metadata,
    }


@router.get("/model/export/formats")
async def list_export_formats():
    return {
        "formats": [
            {
                "id": "onnx",
                "name": "ONNX",
                "description": "Open Neural Network Exchange format — portable, widely supported",
                "available": True,
            },
            {
                "id": "tensorrt",
                "name": "TensorRT",
                "description": "NVIDIA TensorRT optimized inference — requires tensorrt package",
                "available": True,
            },
            {
                "id": "openvino",
                "name": "OpenVINO",
                "description": "Intel OpenVINO optimized inference — requires openvino package",
                "available": True,
            },
        ]
    }
