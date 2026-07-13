import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional

import torch

from models.single_model import SingleModel, SimpleNet
from models.sharded_classifier import ShardedModel, ShardNet

logger = logging.getLogger(__name__)


@dataclass
class ExportResult:
    format: str
    export_path: str
    success: bool
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)


class ModelExportService:
    def __init__(self, export_dir: str = "./exports"):
        self.export_dir = export_dir
        os.makedirs(export_dir, exist_ok=True)

    def _get_torch_model(
        self, model: SingleModel | ShardedModel
    ) -> tuple[torch.nn.Module, int, int]:
        if isinstance(model, SingleModel):
            return model.model, model.input_dim, model.num_classes
        else:
            shard = model.models[0]
            return shard, model.input_dim, model.num_classes

    def export_onnx(
        self,
        model: SingleModel | ShardedModel,
        name: str = "model",
        opset_version: int = 17,
    ) -> ExportResult:
        try:
            torch_model, input_dim, num_classes = self._get_torch_model(model)
            torch_model.eval()

            dummy_input = torch.randn(1, input_dim)
            export_path = os.path.join(self.export_dir, f"{name}.onnx")

            torch.onnx.export(
                torch_model,
                dummy_input,
                export_path,
                export_params=True,
                opset_version=opset_version,
                do_constant_folding=True,
                input_names=["input"],
                output_names=["output"],
                dynamic_axes={
                    "input": {0: "batch_size"},
                    "output": {0: "batch_size"},
                },
            )

            metadata = {
                "input_dim": input_dim,
                "num_classes": num_classes,
                "opset_version": opset_version,
                "framework": "pytorch",
                "model_type": type(torch_model).__name__,
                "file_size_bytes": os.path.getsize(export_path),
            }

            return ExportResult(
                format="onnx",
                export_path=export_path,
                success=True,
                metadata=metadata,
            )
        except (ImportError, ModuleNotFoundError) as e:
            return ExportResult(
                format="onnx",
                export_path="",
                success=False,
                error=f"Missing dependency for ONNX export: {e}. Install with: pip install onnx onnxscript",
            )
        except Exception as e:
            logger.exception("ONNX export failed")
            return ExportResult(format="onnx", export_path="", success=False, error=str(e))

    def export_tensorrt(
        self,
        model: SingleModel | ShardedModel,
        name: str = "model",
        fp16: bool = False,
    ) -> ExportResult:
        try:
            import tensorrt as trt

            onnx_result = self.export_onnx(model, name)
            if not onnx_result.success:
                return ExportResult(
                    format="tensorrt",
                    export_path="",
                    success=False,
                    error=f"ONNX export failed: {onnx_result.error}",
                )

            trt_path = os.path.join(self.export_dir, f"{name}.trt")
            logger = trt.Logger(trt.Logger.WARNING)
            builder = trt.Builder(logger)
            network = builder.create_network(
                1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)
            )
            parser = trt.OnnxParser(network, logger)

            with open(onnx_result.export_path, "rb") as f:
                if not parser.parse(f.read()):
                    errors = [str(parser.get_error(i)) for i in range(parser.num_errors)]
                    return ExportResult(
                        format="tensorrt",
                        export_path="",
                        success=False,
                        error=f"TensorRT ONNX parse failed: {'; '.join(errors)}",
                    )

            config = builder.create_builder_config()
            if fp16 and builder.platform_has_fast_fp16:
                config.set_flag(trt.BuilderFlag.FP16)

            serialized_engine = builder.build_serialized_network(network, config)
            if serialized_engine is None:
                return ExportResult(
                    format="tensorrt",
                    export_path="",
                    success=False,
                    error="TensorRT engine build failed",
                )

            with open(trt_path, "wb") as f:
                f.write(serialized_engine)

            return ExportResult(
                format="tensorrt",
                export_path=trt_path,
                success=True,
                metadata={
                    "fp16": fp16,
                    "input_dim": onnx_result.metadata.get("input_dim"),
                    "num_classes": onnx_result.metadata.get("num_classes"),
                    "file_size_bytes": os.path.getsize(trt_path),
                },
            )
        except ImportError:
            return ExportResult(
                format="tensorrt",
                export_path="",
                success=False,
                error="TensorRT not installed. Install with: pip install tensorrt",
            )
        except Exception as e:
            logger.exception("TensorRT export failed")
            return ExportResult(
                format="tensorrt",
                export_path="",
                success=False,
                error=str(e),
            )

    def export_openvino(
        self,
        model: SingleModel | ShardedModel,
        name: str = "model",
        fp16: bool = False,
    ) -> ExportResult:
        try:
            import openvino as ov
            import openvino.tools.mo as mo

            onnx_result = self.export_onnx(model, name)
            if not onnx_result.success:
                return ExportResult(
                    format="openvino",
                    export_path="",
                    success=False,
                    error=f"ONNX export failed: {onnx_result.error}",
                )

            ov_model = mo.convert_model(onnx_result.export_path)
            ov_path = os.path.join(self.export_dir, f"{name}_openvino")
            os.makedirs(ov_path, exist_ok=True)

            if fp16:
                from openvino.runtime import Core, Type
                core = Core()
                compiled = core.compile_model(ov_model, "CPU")
                ov.save_model(ov_model, os.path.join(ov_path, f"{name}.xml"), compress_to_fp16=True)
            else:
                ov.save_model(ov_model, os.path.join(ov_path, f"{name}.xml"))

            xml_path = os.path.join(ov_path, f"{name}.xml")
            bin_path = os.path.join(ov_path, f"{name}.bin")

            return ExportResult(
                format="openvino",
                export_path=ov_path,
                success=True,
                metadata={
                    "xml_path": xml_path,
                    "bin_path": bin_path,
                    "fp16": fp16,
                    "input_dim": onnx_result.metadata.get("input_dim"),
                    "num_classes": onnx_result.metadata.get("num_classes"),
                    "xml_size_bytes": os.path.getsize(xml_path) if os.path.exists(xml_path) else 0,
                    "bin_size_bytes": os.path.getsize(bin_path) if os.path.exists(bin_path) else 0,
                },
            )
        except ImportError:
            return ExportResult(
                format="openvino",
                export_path="",
                success=False,
                error="OpenVINO not installed. Install with: pip install openvino openvino-tools",
            )
        except Exception as e:
            logger.exception("OpenVINO export failed")
            return ExportResult(
                format="openvino",
                export_path="",
                success=False,
                error=str(e),
            )

    def export_all(
        self,
        model: SingleModel | ShardedModel,
        name: str = "model",
        formats: Optional[list[str]] = None,
    ) -> dict[str, ExportResult]:
        if formats is None:
            formats = ["onnx"]

        results: dict[str, ExportResult] = {}
        for fmt in formats:
            fmt_lower = fmt.lower()
            if fmt_lower == "onnx":
                results["onnx"] = self.export_onnx(model, name)
            elif fmt_lower in ("tensorrt", "trt"):
                results["tensorrt"] = self.export_tensorrt(model, name)
            elif fmt_lower in ("openvino", "ov"):
                results["openvino"] = self.export_openvino(model, name)

        return results
