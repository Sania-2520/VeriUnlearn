import gc
import hashlib
import json
import logging
import os
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Generator, Optional

import torch

logger = logging.getLogger(__name__)

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    from peft import PeftModel
    PEFT_AVAILABLE = True
except ImportError:
    PEFT_AVAILABLE = False

CUDA_AVAILABLE = torch.cuda.is_available()


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class InferenceConfig:
    base_model_name: str = "Qwen/Qwen2.5-0.5B-Instruct"
    device: str = "auto"
    dtype: str = "auto"
    max_new_tokens: int = 1024
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    repetition_penalty: float = 1.1
    do_sample: bool = True
    enable_kv_cache: bool = True
    max_concurrent_requests: int = 10
    request_timeout_seconds: int = 120


@dataclass
class InferenceMetrics:
    total_requests: int = 0
    total_tokens_generated: int = 0
    total_tokens_input: int = 0
    avg_latency_ms: float = 0.0
    avg_tokens_per_second: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    active_requests: int = 0
    errors: int = 0
    adapter_loads: int = 0
    adapter_unloads: int = 0
    uptime_seconds: float = 0.0
    last_request_at: Optional[str] = None
    memory_used_mb: float = 0.0
    gpu_memory_used_mb: float = 0.0


@dataclass
class InferenceRequest:
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    prompt: str = ""
    max_new_tokens: int = 1024
    temperature: float = 0.7
    top_p: float = 0.9
    stream: bool = False
    adapter_name: Optional[str] = None
    system_prompt: Optional[str] = None
    stop_sequences: list[str] = field(default_factory=list)


@dataclass
class InferenceResponse:
    request_id: str
    text: str
    tokens_generated: int
    tokens_input: int
    latency_ms: float
    tokens_per_second: float
    finish_reason: str
    adapter_used: Optional[str]
    model_used: str
    created_at: str


# ---------------------------------------------------------------------------
# AdapterManager
# ---------------------------------------------------------------------------

class AdapterManager:
    def __init__(self, base_model_name: str, device: str) -> None:
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers is required for AdapterManager")
        self._base_model_name = base_model_name
        self._device_str = device
        self._loaded_adapters: dict[str, Any] = {}
        self._base_model: Any = None
        self._tokenizer: Any = None
        self._lock = threading.RLock()

        if device == "auto":
            if CUDA_AVAILABLE:
                self._device = torch.device("cuda")
            else:
                self._device = torch.device("cpu")
        else:
            self._device = torch.device(device)

    def load_base_model(self) -> None:
        with self._lock:
            if self._base_model is not None:
                return

            logger.info("Loading base model: %s on %s", self._base_model_name, self._device)

            tokenizer = AutoTokenizer.from_pretrained(
                self._base_model_name,
                trust_remote_code=True,
            )
            if tokenizer.pad_token_id is None:
                tokenizer.pad_token_id = tokenizer.eos_token_id

            dtype = self._resolve_dtype()

            model_kwargs: dict[str, Any] = {
                "trust_remote_code": True,
                "torch_dtype": dtype,
            }

            if self._device.type == "cuda":
                model_kwargs["device_map"] = "auto"
            else:
                model_kwargs["device_map"] = None

            model = AutoModelForCausalLM.from_pretrained(
                self._base_model_name,
                **model_kwargs,
            )

            if self._device.type == "cpu":
                model = model.to(self._device)

            if self._device.type == "cuda":
                model.eval()
                if hasattr(model, "half") and dtype == torch.float16:
                    model = model.half()

            self._tokenizer = tokenizer
            self._base_model = model
            logger.info(
                "Base model loaded — params: %.2fM, device: %s, dtype: %s",
                sum(p.numel() for p in model.parameters()) / 1e6,
                self._device,
                dtype,
            )

    def load_adapter(self, adapter_name: str, adapter_path: str) -> Any:
        with self._lock:
            if adapter_name in self._loaded_adapters:
                logger.info("Adapter '%s' already loaded, returning cached", adapter_name)
                return self._loaded_adapters[adapter_name]

            if not PEFT_AVAILABLE:
                raise ImportError("peft is required to load LoRA adapters")

            import os
            if not os.path.isdir(adapter_path):
                raise FileNotFoundError(f"Adapter path does not exist: {adapter_path}")

            self.load_base_model()

            logger.info("Loading adapter '%s' from %s", adapter_name, adapter_path)
            adapter_model = PeftModel.from_pretrained(
                self._base_model,
                adapter_path,
                adapter_name=adapter_name,
            )
            adapter_model.eval()
            self._loaded_adapters[adapter_name] = adapter_model
            logger.info("Adapter '%s' loaded successfully", adapter_name)
            return adapter_model

    def unload_adapter(self, adapter_name: str) -> bool:
        with self._lock:
            if adapter_name not in self._loaded_adapters:
                logger.warning("Adapter '%s' not found in loaded adapters", adapter_name)
                return False

            adapter_model = self._loaded_adapters.pop(adapter_name)

            if hasattr(adapter_model, "unload"):
                try:
                    adapter_model.unload()
                except Exception as exc:
                    logger.warning("Error unloading adapter '%s': %s", adapter_name, exc)

            del adapter_model
            gc.collect()
            if CUDA_AVAILABLE:
                torch.cuda.empty_cache()

            logger.info("Adapter '%s' unloaded", adapter_name)
            return True

    def get_model(self, adapter_name: Optional[str] = None) -> Any:
        with self._lock:
            if adapter_name is None:
                return self._base_model

            if adapter_name in self._loaded_adapters:
                return self._loaded_adapters[adapter_name]

            raise KeyError(f"Adapter '{adapter_name}' is not loaded")

    def get_tokenizer(self) -> Any:
        with self._lock:
            return self._tokenizer

    def swap_adapter(
        self,
        old_adapter: Optional[str],
        new_adapter: str,
        new_adapter_path: str,
    ) -> Any:
        with self._lock:
            if old_adapter and old_adapter in self._loaded_adapters:
                self._unload_adapter_internal(old_adapter)

            return self.load_adapter(new_adapter, new_adapter_path)

    def list_loaded_adapters(self) -> list[str]:
        with self._lock:
            return list(self._loaded_adapters.keys())

    def clear_cache(self) -> None:
        with self._lock:
            self._unload_all_adapters()
            if self._base_model is not None:
                del self._base_model
                self._base_model = None
            gc.collect()
            if CUDA_AVAILABLE:
                torch.cuda.empty_cache()
            logger.info("All adapters unloaded, base model freed")

    def get_memory_usage(self) -> dict:
        mem_info: dict[str, Any] = {
            "device": str(self._device),
            "cuda_available": CUDA_AVAILABLE,
            "base_model_loaded": self._base_model is not None,
            "loaded_adapters": list(self._loaded_adapters.keys()),
            "adapter_count": len(self._loaded_adapters),
        }

        if self._device.type == "cuda" and CUDA_AVAILABLE:
            mem_info["gpu_memory_allocated_mb"] = round(
                torch.cuda.memory_allocated(self._device) / (1024 ** 2), 2
            )
            mem_info["gpu_memory_reserved_mb"] = round(
                torch.cuda.memory_reserved(self._device) / (1024 ** 2), 2
            )
            mem_info["gpu_max_allocated_mb"] = round(
                torch.cuda.max_memory_allocated(self._device) / (1024 ** 2), 2
            )

        if self._base_model is not None:
            total_params = sum(p.numel() for p in self._base_model.parameters())
            mem_info["base_model_params"] = total_params
            mem_info["base_model_params_m"] = round(total_params / 1e6, 2)

        return mem_info

    def _unload_all_adapters(self) -> None:
        for name in list(self._loaded_adapters.keys()):
            self._unload_adapter_internal(name)

    def _unload_adapter_internal(self, adapter_name: str) -> None:
        adapter_model = self._loaded_adapters.pop(adapter_name, None)
        if adapter_model is not None:
            if hasattr(adapter_model, "unload"):
                try:
                    adapter_model.unload()
                except Exception:
                    logger.debug("Error unloading adapter '%s' (internal)", adapter_name, exc_info=True)
            del adapter_model

    def _resolve_dtype(self) -> torch.dtype:
        dtype_str = getattr(self, "_dtype_str", "auto")
        if hasattr(self, "_config"):
            dtype_str = self._config.dtype

        if dtype_str == "float16":
            return torch.float16
        elif dtype_str == "bfloat16":
            return torch.bfloat16
        elif dtype_str == "float32":
            return torch.float32
        elif dtype_str == "auto":
            if self._device.type == "cuda":
                if torch.cuda.is_bf16_supported():
                    return torch.bfloat16
                return torch.float16
            return torch.float32
        return torch.float32


# ---------------------------------------------------------------------------
# InferenceService
# ---------------------------------------------------------------------------

class InferenceService:
    def __init__(self, config: Optional[InferenceConfig] = None) -> None:
        self.config = config or InferenceConfig()
        self.adapter_manager = AdapterManager(
            self.config.base_model_name,
            self.config.device,
        )
        self.adapter_manager._config = self.config
        self.metrics = InferenceMetrics()
        self._request_history: deque[float] = deque(maxlen=1000)
        self._start_time = time.monotonic()
        self._lock = threading.RLock()
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return

        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers is required for InferenceService")

        logger.info(
            "Initializing inference service — model: %s, device: %s",
            self.config.base_model_name,
            self.config.device,
        )

        self.adapter_manager.load_base_model()
        self._initialized = True
        logger.info("Inference service initialized successfully")

    def generate(self, request: InferenceRequest) -> InferenceResponse:
        t_start = time.monotonic()

        with self._lock:
            self.metrics.active_requests += 1
            self.metrics.last_request_at = datetime.now(timezone.utc).isoformat()

        try:
            model = self.adapter_manager.get_model(request.adapter_name)
            tokenizer = self.adapter_manager.get_tokenizer()

            if model is None or tokenizer is None:
                raise RuntimeError("Model not initialized — call initialize() first")

            prompt_text = self._format_prompt(request, tokenizer)
            inputs = tokenizer(
                prompt_text,
                return_tensors="pt",
                truncation=True,
                max_length=4096,
            )

            input_device = self.adapter_manager._device
            input_ids = inputs["input_ids"].to(input_device)
            attention_mask = inputs["attention_mask"].to(input_device)
            tokens_input = input_ids.shape[1]

            gen_kwargs: dict[str, Any] = {
                "max_new_tokens": request.max_new_tokens,
                "do_sample": self.config.do_sample,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "top_k": self.config.top_k,
                "repetition_penalty": self.config.repetition_penalty,
                "pad_token_id": tokenizer.pad_token_id or tokenizer.eos_token_id,
            }

            if not self.config.enable_kv_cache:
                gen_kwargs["use_cache"] = False

            if request.stop_sequences:
                stop_token_ids = []
                for seq in request.stop_sequences:
                    encoded = tokenizer.encode(seq, add_special_tokens=False)
                    if encoded:
                        stop_token_ids.extend(encoded)
                if stop_token_ids:
                    gen_kwargs["eos_token_id"] = stop_token_ids

            with torch.no_grad():
                output_ids = model.generate(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    **gen_kwargs,
                )

            generated_ids = output_ids[0][tokens_input:]
            tokens_generated = len(generated_ids)
            response_text = tokenizer.decode(generated_ids, skip_special_tokens=True)

            finish_reason = "stop"
            if tokens_generated >= request.max_new_tokens:
                finish_reason = "length"

            if request.stop_sequences:
                for seq in request.stop_sequences:
                    if seq in response_text:
                        response_text = response_text[:response_text.index(seq)]
                        finish_reason = "stop"
                        break

            t_end = time.monotonic()
            latency_ms = (t_end - t_start) * 1000
            tokens_per_second = (
                tokens_generated / (latency_ms / 1000) if latency_ms > 0 else 0.0
            )

            self._update_metrics(tokens_input, tokens_generated, latency_ms)

            response = InferenceResponse(
                request_id=request.request_id,
                text=response_text.strip(),
                tokens_generated=tokens_generated,
                tokens_input=tokens_input,
                latency_ms=round(latency_ms, 2),
                tokens_per_second=round(tokens_per_second, 2),
                finish_reason=finish_reason,
                adapter_used=request.adapter_name,
                model_used=self.config.base_model_name,
                created_at=datetime.now(timezone.utc).isoformat(),
            )

            return response

        except Exception as exc:
            with self._lock:
                self.metrics.errors += 1
            logger.error("Generation failed for request %s: %s", request.request_id, exc)

            t_end = time.monotonic()
            latency_ms = (t_end - t_start) * 1000

            return InferenceResponse(
                request_id=request.request_id,
                text="",
                tokens_generated=0,
                tokens_input=0,
                latency_ms=round(latency_ms, 2),
                tokens_per_second=0.0,
                finish_reason="error",
                adapter_used=request.adapter_name,
                model_used=self.config.base_model_name,
                created_at=datetime.now(timezone.utc).isoformat(),
            )

        finally:
            with self._lock:
                self.metrics.active_requests = max(0, self.metrics.active_requests - 1)

    def generate_stream(
        self,
        request: InferenceRequest,
    ) -> Generator[str, None, None]:
        t_start = time.monotonic()

        with self._lock:
            self.metrics.active_requests += 1
            self.metrics.last_request_at = datetime.now(timezone.utc).isoformat()

        try:
            model = self.adapter_manager.get_model(request.adapter_name)
            tokenizer = self.adapter_manager.get_tokenizer()

            if model is None or tokenizer is None:
                raise RuntimeError("Model not initialized — call initialize() first")

            if not TRANSFORMERS_AVAILABLE:
                raise ImportError("transformers TextIteratorStreamer is required for streaming")

            prompt_text = self._format_prompt(request, tokenizer)
            inputs = tokenizer(
                prompt_text,
                return_tensors="pt",
                truncation=True,
                max_length=4096,
            )

            input_device = self.adapter_manager._device
            input_ids = inputs["input_ids"].to(input_device)
            attention_mask = inputs["attention_mask"].to(input_device)
            tokens_input = input_ids.shape[1]

            streamer = TextIteratorStreamer(
                tokenizer,
                skip_prompt=True,
                skip_special_tokens=True,
            )

            gen_kwargs: dict[str, Any] = {
                "max_new_tokens": request.max_new_tokens,
                "do_sample": self.config.do_sample,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "top_k": self.config.top_k,
                "repetition_penalty": self.config.repetition_penalty,
                "pad_token_id": tokenizer.pad_token_id or tokenizer.eos_token_id,
                "streamer": streamer,
            }

            if not self.config.enable_kv_cache:
                gen_kwargs["use_cache"] = False

            if request.stop_sequences:
                stop_token_ids = []
                for seq in request.stop_sequences:
                    encoded = tokenizer.encode(seq, add_special_tokens=False)
                    if encoded:
                        stop_token_ids.extend(encoded)
                if stop_token_ids:
                    gen_kwargs["eos_token_id"] = stop_token_ids

            thread = threading.Thread(
                target=self._stream_generate,
                args=(model, input_ids, attention_mask, gen_kwargs),
                daemon=True,
            )
            thread.start()

            tokens_generated = 0
            for text_chunk in streamer:
                if text_chunk:
                    tokens_generated += 1
                    yield text_chunk

            thread.join(timeout=self.config.request_timeout_seconds)

            t_end = time.monotonic()
            latency_ms = (t_end - t_start) * 1000
            tokens_per_second = (
                tokens_generated / (latency_ms / 1000) if latency_ms > 0 else 0.0
            )

            self._update_metrics(tokens_input, tokens_generated, latency_ms)

        except Exception as exc:
            with self._lock:
                self.metrics.errors += 1
            logger.error("Stream generation failed: %s", exc)
            yield f"[ERROR: {exc}]"

        finally:
            with self._lock:
                self.metrics.active_requests = max(0, self.metrics.active_requests - 1)

    def _stream_generate(
        self,
        model: Any,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        gen_kwargs: dict[str, Any],
    ) -> None:
        try:
            with torch.no_grad():
                model.generate(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    **gen_kwargs,
                )
        except Exception as exc:
            logger.error("Stream generation thread error: %s", exc)

    def batch_generate(
        self,
        requests: list[InferenceRequest],
    ) -> list[InferenceResponse]:
        responses: list[InferenceResponse] = []
        for request in requests:
            response = self.generate(request)
            responses.append(response)
        return responses

    def load_adapter(self, name: str, path: str) -> dict:
        try:
            self.adapter_manager.load_adapter(name, path)
            with self._lock:
                self.metrics.adapter_loads += 1
            return {
                "status": "loaded",
                "adapter_name": name,
                "adapter_path": path,
                "loaded_adapters": self.adapter_manager.list_loaded_adapters(),
            }
        except Exception as exc:
            logger.error("Failed to load adapter '%s': %s", name, exc)
            return {
                "status": "error",
                "adapter_name": name,
                "error": str(exc),
            }

    def unload_adapter(self, name: str) -> dict:
        success = self.adapter_manager.unload_adapter(name)
        if success:
            with self._lock:
                self.metrics.adapter_unloads += 1
            return {
                "status": "unloaded",
                "adapter_name": name,
                "loaded_adapters": self.adapter_manager.list_loaded_adapters(),
            }
        return {
            "status": "not_found",
            "adapter_name": name,
            "loaded_adapters": self.adapter_manager.list_loaded_adapters(),
        }

    def get_metrics(self) -> InferenceMetrics:
        with self._lock:
            metrics = InferenceMetrics(
                total_requests=self.metrics.total_requests,
                total_tokens_generated=self.metrics.total_tokens_generated,
                total_tokens_input=self.metrics.total_tokens_input,
                avg_latency_ms=self.metrics.avg_latency_ms,
                avg_tokens_per_second=self.metrics.avg_tokens_per_second,
                p95_latency_ms=self.metrics.p95_latency_ms,
                p99_latency_ms=self.metrics.p99_latency_ms,
                active_requests=self.metrics.active_requests,
                errors=self.metrics.errors,
                adapter_loads=self.metrics.adapter_loads,
                adapter_unloads=self.metrics.adapter_unloads,
                uptime_seconds=round(time.monotonic() - self._start_time, 2),
                last_request_at=self.metrics.last_request_at,
                memory_used_mb=0.0,
                gpu_memory_used_mb=0.0,
            )

        mem = self.adapter_manager.get_memory_usage()
        if mem.get("cuda_available") and mem.get("gpu_memory_allocated_mb"):
            metrics.gpu_memory_used_mb = mem["gpu_memory_allocated_mb"]

        if CUDA_AVAILABLE:
            metrics.gpu_memory_used_mb = round(
                torch.cuda.memory_allocated() / (1024 ** 2), 2
            )

        return metrics

    def get_health(self) -> dict:
        model = self.adapter_manager._base_model
        tokenizer = self.adapter_manager._tokenizer

        return {
            "status": "healthy" if model is not None else "not_ready",
            "initialized": self._initialized,
            "base_model_loaded": model is not None,
            "tokenizer_loaded": tokenizer is not None,
            "base_model_name": self.config.base_model_name,
            "device": str(self.adapter_manager._device),
            "loaded_adapters": self.adapter_manager.list_loaded_adapters(),
            "adapter_count": len(self.adapter_manager.list_loaded_adapters()),
            "total_requests": self.metrics.total_requests,
            "active_requests": self.metrics.active_requests,
            "errors": self.metrics.errors,
            "uptime_seconds": round(time.monotonic() - self._start_time, 2),
            "transformers_available": TRANSFORMERS_AVAILABLE,
            "peft_available": PEFT_AVAILABLE,
            "cuda_available": CUDA_AVAILABLE,
        }

    def _update_metrics(
        self,
        tokens_input: int,
        tokens_generated: int,
        latency_ms: float,
    ) -> None:
        with self._lock:
            self.metrics.total_requests += 1
            self.metrics.total_tokens_generated += tokens_generated
            self.metrics.total_tokens_input += tokens_input

            total = self.metrics.total_requests
            self.metrics.avg_latency_ms = (
                (self.metrics.avg_latency_ms * (total - 1) + latency_ms) / total
            )

            if latency_ms > 0:
                current_tps = tokens_generated / (latency_ms / 1000)
                self.metrics.avg_tokens_per_second = (
                    (self.metrics.avg_tokens_per_second * (total - 1) + current_tps) / total
                )

            self._request_history.append(latency_ms)
            if len(self._request_history) >= 2:
                sorted_latencies = sorted(self._request_history)
                n = len(sorted_latencies)
                p95_idx = min(int(n * 0.95), n - 1)
                p99_idx = min(int(n * 0.99), n - 1)
                self.metrics.p95_latency_ms = sorted_latencies[p95_idx]
                self.metrics.p99_latency_ms = sorted_latencies[p99_idx]

    def shutdown(self) -> None:
        logger.info("Shutting down inference service")
        self.adapter_manager.clear_cache()
        gc.collect()
        if CUDA_AVAILABLE:
            torch.cuda.empty_cache()
        self._initialized = False
        logger.info("Inference service shut down")

    def _format_prompt(self, request: InferenceRequest, tokenizer: Any) -> str:
        has_chat_template = (
            hasattr(tokenizer, "apply_chat_template")
            and getattr(tokenizer, "chat_template", None) is not None
        )

        if has_chat_template:
            messages: list[dict[str, str]] = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.prompt})
            return tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )

        parts: list[str] = []
        if request.system_prompt:
            parts.append(f"System: {request.system_prompt}\n")
        parts.append(f"User: {request.prompt}\nAssistant:")
        return "\n".join(parts)
