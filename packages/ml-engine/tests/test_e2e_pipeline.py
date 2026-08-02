import asyncio
import uuid

import pytest

from unlearning.e2e_pipeline import (
    DeletionCertificate,
    DeletionRequest,
    E2EUnlearningPipeline,
    PipelineStep,
)

pytestmark = pytest.mark.slow


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestDeletionRequest:
    def test_creation_defaults(self):
        req = DeletionRequest()
        assert req.request_id  # UUID generated
        assert req.tenant_id == ""
        assert req.user_id == ""
        assert req.target_data_ids == []
        assert req.model_name == ""
        assert req.status == "pending"
        assert req.regulatory == "gdpr"
        assert req.priority == "medium"
        assert req.created_at is not None

    def test_creation_explicit(self):
        req = DeletionRequest(
            tenant_id="t1",
            user_id="u1",
            target_data_ids=["d1", "d2"],
            model_name="my-model",
            regulatory="ccpa",
            priority="high",
        )
        assert req.tenant_id == "t1"
        assert req.user_id == "u1"
        assert req.target_data_ids == ["d1", "d2"]
        assert req.regulatory == "ccpa"
        assert req.priority == "high"

    def test_unique_request_ids(self):
        r1 = DeletionRequest()
        r2 = DeletionRequest()
        assert r1.request_id != r2.request_id

    def test_metadata_default_empty(self):
        req = DeletionRequest()
        assert req.metadata == {}

    def test_model_version_id_optional(self):
        req = DeletionRequest()
        assert req.model_version_id is None


class TestDeletionCertificate:
    def test_creation(self):
        cert = DeletionCertificate()
        assert cert.certificate_id
        assert cert.version == "1.0"
        assert cert.status == "generated"
        assert cert.created_at is not None
        assert cert.expires_at == ""

    def test_creation_explicit(self):
        cert = DeletionCertificate(
            request_id="r1",
            algorithm="sisa",
            target_data_ids=["d1"],
            utility_retained=0.95,
        )
        assert cert.request_id == "r1"
        assert cert.algorithm == "sisa"
        assert cert.utility_retained == 0.95


class TestPipelineStep:
    def test_creation(self):
        step = PipelineStep(step_id="s1", name="test_step")
        assert step.step_id == "s1"
        assert step.name == "test_step"
        assert step.status == "pending"
        assert step.started_at is None
        assert step.error is None

    def test_with_result(self):
        step = PipelineStep(
            step_id="s1",
            name="step",
            status="completed",
            result={"key": "value"},
        )
        assert step.status == "completed"
        assert step.result["key"] == "value"


class TestE2EUnlearningPipeline:
    @pytest.fixture
    def pipeline(self):
        return E2EUnlearningPipeline()

    def test_init(self, pipeline):
        assert pipeline.controller is not None
        assert pipeline.signature_manager is not None
        assert pipeline.privacy_evaluator is not None
        assert pipeline.zk_service is not None
        assert pipeline._pipeline_history == []

    def test_full_pipeline(self, pipeline):
        request = DeletionRequest(
            tenant_id="test",
            user_id="user1",
            target_data_ids=["data_000001", "data_000002"],
            model_name="test-model",
        )
        result = _run_async(pipeline.execute_full_pipeline(request))
        assert result["request"]["status"] == "completed"
        assert "certificate" in result
        assert "steps" in result
        assert len(result["steps"]) == 12
        assert result["total_duration_ms"] >= 0

    def test_pipeline_steps_all_complete(self, pipeline):
        request = DeletionRequest(
            target_data_ids=["data_000001"],
            model_name="test-model",
        )
        result = _run_async(pipeline.execute_full_pipeline(request))
        for step in result["steps"]:
            assert step["status"] == "completed", f"Step {step['name']} failed: {step.get('error')}"

    def test_pipeline_request_status_completed(self, pipeline):
        request = DeletionRequest(
            target_data_ids=["data_000001", "data_000002", "data_000003"],
            model_name="m",
        )
        _run_async(pipeline.execute_full_pipeline(request))
        assert request.status == "completed"

    def test_certificate_in_result(self, pipeline):
        request = DeletionRequest(
            target_data_ids=["data_000001"],
            model_name="m",
        )
        result = _run_async(pipeline.execute_full_pipeline(request))
        cert = result["certificate"]
        assert cert is not None
        assert cert["certificate_id"]
        assert cert["algorithm"]

    def test_certificate_verification(self, pipeline):
        request = DeletionRequest(
            target_data_ids=["data_000001"],
            model_name="m",
        )
        result = _run_async(pipeline.execute_full_pipeline(request))
        cert = result["certificate"]
        assert cert is not None
        assert cert["sha256"]
        assert len(cert["sha256"]) == 64
        assert cert["merkle_root"]

    def test_verify_certificate_method(self, pipeline):
        request = DeletionRequest(
            target_data_ids=["data_000001"],
            model_name="m",
        )
        result = _run_async(pipeline.execute_full_pipeline(request))
        from unlearning.e2e_pipeline import DeletionCertificate
        cert = DeletionCertificate(
            request_id=request.request_id,
            algorithm="SISA",
            target_data_ids=request.target_data_ids,
            unlearning_result={"success": True, "algorithm": "SISA"},
            utility_retained=0.9,
            sha256="a" * 64,
            merkle_root="b" * 64,
            signature_hex="c" * 64,
            public_key_pem="-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOC\n-----END PUBLIC KEY-----",
        )
        verification = pipeline.verify_certificate(cert)
        assert "overall_valid" in verification
        assert "checks" in verification

    def test_pipeline_history(self, pipeline):
        request = DeletionRequest(
            target_data_ids=["data_000001"],
            model_name="m",
        )
        _run_async(pipeline.execute_full_pipeline(request))
        history = pipeline.get_pipeline_history()
        assert len(history) == 1
        assert history[0]["pipeline_id"]

    def test_pipeline_stats(self, pipeline):
        stats = pipeline.get_pipeline_stats()
        assert stats["total_pipelines"] == 0
        assert stats["success_rate"] == 0.0

        request = DeletionRequest(
            target_data_ids=["data_000001"],
            model_name="m",
        )
        _run_async(pipeline.execute_full_pipeline(request))
        stats = pipeline.get_pipeline_stats()
        assert stats["total_pipelines"] == 1
        assert stats["successful_pipelines"] == 1
        assert stats["success_rate"] == 1.0

    def test_dashboard_data_in_result(self, pipeline):
        request = DeletionRequest(
            target_data_ids=["data_000001"],
            model_name="m",
        )
        result = _run_async(pipeline.execute_full_pipeline(request))
        dashboard_step = [s for s in result["steps"] if s["name"] == "prepare_dashboard_data"]
        assert len(dashboard_step) == 1
        assert dashboard_step[0]["status"] == "completed"

    def test_multiple_pipeline_runs(self, pipeline):
        for i in range(3):
            request = DeletionRequest(
                target_data_ids=[f"data_{i:06d}"],
                model_name="m",
            )
            _run_async(pipeline.execute_full_pipeline(request))
        stats = pipeline.get_pipeline_stats()
        assert stats["total_pipelines"] == 3

    def test_pipeline_result_structure(self, pipeline):
        request = DeletionRequest(
            target_data_ids=["data_000001", "data_000002"],
            model_name="m",
            tenant_id="t1",
            user_id="u1",
        )
        result = _run_async(pipeline.execute_full_pipeline(request))
        assert "pipeline_id" in result
        assert "request" in result
        assert result["request"]["tenant_id"] == "t1"
        assert result["request"]["num_target_samples"] == 2
        assert "completed_at" in result
