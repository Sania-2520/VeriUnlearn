import time

import pytest
import torch

from inference.service import (
    AdapterManager,
    InferenceConfig,
    InferenceMetrics,
    InferenceRequest,
    InferenceResponse,
    InferenceService,
)


class TestInferenceConfig:
    def test_default_config(self):
        config = InferenceConfig()
        assert config.base_model_name == "Qwen/Qwen2.5-0.5B-Instruct"
        assert config.device == "auto"
        assert config.max_new_tokens == 1024
        assert config.temperature == 0.7
        assert config.top_p == 0.9
        assert config.top_k == 50
        assert config.repetition_penalty == 1.1
        assert config.do_sample is True
        assert config.enable_kv_cache is True
        assert config.max_concurrent_requests == 10

    def test_custom_config(self):
        config = InferenceConfig(
            base_model_name="custom-model",
            device="cpu",
            max_new_tokens=256,
            temperature=0.5,
        )
        assert config.base_model_name == "custom-model"
        assert config.device == "cpu"
        assert config.max_new_tokens == 256
        assert config.temperature == 0.5


class TestInferenceMetrics:
    def test_default_metrics(self):
        metrics = InferenceMetrics()
        assert metrics.total_requests == 0
        assert metrics.total_tokens_generated == 0
        assert metrics.total_tokens_input == 0
        assert metrics.avg_latency_ms == 0.0
        assert metrics.avg_tokens_per_second == 0.0
        assert metrics.p95_latency_ms == 0.0
        assert metrics.p99_latency_ms == 0.0
        assert metrics.active_requests == 0
        assert metrics.errors == 0
        assert metrics.adapter_loads == 0
        assert metrics.adapter_unloads == 0
        assert metrics.last_request_at is None

    def test_custom_metrics(self):
        metrics = InferenceMetrics(
            total_requests=10,
            avg_latency_ms=50.0,
            errors=2,
        )
        assert metrics.total_requests == 10
        assert metrics.avg_latency_ms == 50.0
        assert metrics.errors == 2


class TestInferenceRequest:
    def test_default_request(self):
        req = InferenceRequest(prompt="hello")
        assert req.request_id  # UUID generated
        assert req.prompt == "hello"
        assert req.max_new_tokens == 1024
        assert req.temperature == 0.7
        assert req.stream is False
        assert req.adapter_name is None
        assert req.system_prompt is None
        assert req.stop_sequences == []

    def test_unique_request_ids(self):
        r1 = InferenceRequest(prompt="a")
        r2 = InferenceRequest(prompt="b")
        assert r1.request_id != r2.request_id


class TestInferenceResponse:
    def test_creation(self):
        resp = InferenceResponse(
            request_id="r1",
            text="hello",
            tokens_generated=5,
            tokens_input=3,
            latency_ms=100.0,
            tokens_per_second=50.0,
            finish_reason="stop",
            adapter_used=None,
            model_used="test-model",
            created_at="2024-01-01T00:00:00",
        )
        assert resp.request_id == "r1"
        assert resp.text == "hello"
        assert resp.tokens_generated == 5
        assert resp.finish_reason == "stop"


class TestAdapterManager:
    def test_init(self):
        from inference.service import TRANSFORMERS_AVAILABLE
        if not TRANSFORMERS_AVAILABLE:
            pytest.skip("transformers not installed")
        manager = AdapterManager("Qwen/Qwen2.5-0.5B-Instruct", "cpu")
        assert manager._base_model is None
        assert manager._tokenizer is None
        assert manager._loaded_adapters == {}

    def test_list_loaded_adapters_empty(self):
        from inference.service import TRANSFORMERS_AVAILABLE
        if not TRANSFORMERS_AVAILABLE:
            pytest.skip("transformers not installed")
        manager = AdapterManager("Qwen/Qwen2.5-0.5B-Instruct", "cpu")
        assert manager.list_loaded_adapters() == []

    def test_get_model_no_base(self):
        from inference.service import TRANSFORMERS_AVAILABLE
        if not TRANSFORMERS_AVAILABLE:
            pytest.skip("transformers not installed")
        manager = AdapterManager("Qwen/Qwen2.5-0.5B-Instruct", "cpu")
        assert manager.get_model() is None
        assert manager.get_tokenizer() is None

    def test_get_model_missing_adapter_raises(self):
        from inference.service import TRANSFORMERS_AVAILABLE
        if not TRANSFORMERS_AVAILABLE:
            pytest.skip("transformers not installed")
        manager = AdapterManager("Qwen/Qwen2.5-0.5B-Instruct", "cpu")
        with pytest.raises(KeyError):
            manager.get_model("nonexistent-adapter")

    def test_unload_adapter_not_found(self):
        from inference.service import TRANSFORMERS_AVAILABLE
        if not TRANSFORMERS_AVAILABLE:
            pytest.skip("transformers not installed")
        manager = AdapterManager("Qwen/Qwen2.5-0.5B-Instruct", "cpu")
        result = manager.unload_adapter("nonexistent")
        assert result is False

    def test_get_memory_usage(self):
        from inference.service import TRANSFORMERS_AVAILABLE
        if not TRANSFORMERS_AVAILABLE:
            pytest.skip("transformers not installed")
        manager = AdapterManager("Qwen/Qwen2.5-0.5B-Instruct", "cpu")
        mem = manager.get_memory_usage()
        assert "device" in mem
        assert "cuda_available" in mem
        assert "base_model_loaded" in mem
        assert "loaded_adapters" in mem
        assert mem["base_model_loaded"] is False

    def test_clear_cache(self):
        from inference.service import TRANSFORMERS_AVAILABLE
        if not TRANSFORMERS_AVAILABLE:
            pytest.skip("transformers not installed")
        manager = AdapterManager("Qwen/Qwen2.5-0.5B-Instruct", "cpu")
        manager.clear_cache()
        assert manager._base_model is None


class TestInferenceService:
    def test_init(self):
        config = InferenceConfig(device="cpu")
        service = InferenceService(config)
        assert service.config == config
        assert service.adapter_manager is not None
        assert service.metrics is not None

    def test_init_default_config(self):
        service = InferenceService()
        assert service.config.base_model_name == "Qwen/Qwen2.5-0.5B-Instruct"

    def test_metrics_initial(self):
        service = InferenceService()
        metrics = service.get_metrics()
        assert metrics.total_requests == 0
        assert metrics.avg_latency_ms == 0.0
        assert metrics.errors == 0
        assert metrics.uptime_seconds >= 0

    def test_health_not_initialized(self):
        service = InferenceService()
        health = service.get_health()
        assert health["status"] == "not_ready"
        assert health["initialized"] is False
        assert health["base_model_loaded"] is False

    def test_get_health_keys(self):
        service = InferenceService()
        health = service.get_health()
        expected_keys = [
            "status", "initialized", "base_model_loaded", "tokenizer_loaded",
            "base_model_name", "device", "loaded_adapters", "adapter_count",
            "total_requests", "active_requests", "errors", "uptime_seconds",
            "transformers_available", "peft_available", "cuda_available",
        ]
        for key in expected_keys:
            assert key in health

    def test_load_adapter_error_handling(self):
        service = InferenceService()
        result = service.load_adapter("test_adapter", "/nonexistent/path")
        assert result["status"] == "error"

    def test_unload_adapter_not_found(self):
        service = InferenceService()
        result = service.unload_adapter("nonexistent")
        assert result["status"] == "not_found"

    def test_batch_generate_empty(self):
        service = InferenceService()
        results = service.batch_generate([])
        assert results == []

    def test_shutdown(self):
        service = InferenceService()
        service.shutdown()
        assert service._initialized is False

    def test_format_prompt_no_template(self):
        service = InferenceService()

        class MockTokenizer:
            chat_template = None
            def apply_chat_template(self, *a, **kw):
                return ""

        req = InferenceRequest(prompt="Hello", system_prompt="You are helpful")
        prompt = service._format_prompt(req, MockTokenizer())
        assert "Hello" in prompt
        assert "You are helpful" in prompt

    def test_format_prompt_no_system(self):
        service = InferenceService()

        class MockTokenizer:
            chat_template = None

        req = InferenceRequest(prompt="Hello")
        prompt = service._format_prompt(req, MockTokenizer())
        assert "Hello" in prompt
        assert "Assistant" in prompt

    def test_update_metrics(self):
        service = InferenceService()
        service._update_metrics(10, 20, 100.0)
        assert service.metrics.total_requests == 1
        assert service.metrics.total_tokens_input == 10
        assert service.metrics.total_tokens_generated == 20
        assert service.metrics.avg_latency_ms > 0

    def test_update_metrics_percentiles(self):
        service = InferenceService()
        for i in range(20):
            service._update_metrics(5, 10, float(i * 10))
        assert service.metrics.p95_latency_ms > 0
        assert service.metrics.p99_latency_ms > 0
