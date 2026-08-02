import pytest
import torch

from unlearning.algorithms.base import UnlearningContext
from unlearning.algorithms.certified_removal import CertifiedRemovalUnlearning
from unlearning.algorithms.influence import InfluenceFunctionUnlearning
from unlearning.algorithms.sisa import SISAUnlearning


@pytest.mark.asyncio
class TestSISAAlgorithm:
    async def test_unlearn_returns_success(self):
        algo = SISAUnlearning(num_shards=4)
        context = UnlearningContext(
            target_data_ids=["data_000000", "data_000001"],
            data_size=100,
            model_name="sisa_test_model",
        )
        result = await algo.unlearn(context)
        assert result.success is True
        assert result.algorithm == "SISA"
        assert result.processing_time_ms >= 0
        assert result.metrics["shards_affected"] >= 1
        assert result.metrics["shards_total"] == 4

    async def test_unlearn_removes_target_data(self):
        algo = SISAUnlearning(num_shards=4)
        context = UnlearningContext(
            target_data_ids=["data_000005", "data_000010"],
            data_size=100,
            model_name="sisa_verify_test",
        )
        await algo.unlearn(context)
        is_valid = await algo.verify(context)
        assert is_valid is True

    async def test_multiple_calls_accumulate(self):
        algo = SISAUnlearning(num_shards=4)
        ctx1 = UnlearningContext(
            target_data_ids=["data_000000", "data_000001"],
            data_size=100,
            model_name="sisa_multi_test",
        )
        r1 = await algo.unlearn(ctx1)
        assert r1.success is True

        ctx2 = UnlearningContext(
            target_data_ids=["data_000002", "data_000003"],
            data_size=100,
            model_name="sisa_multi_test",
        )
        r2 = await algo.unlearn(ctx2)
        assert r2.success is True
        assert r2.metrics["shards_total"] == 4

    async def test_verify_fails_if_data_not_removed(self):
        algo = SISAUnlearning(num_shards=4)
        context = UnlearningContext(
            target_data_ids=["data_000000"],
            data_size=50,
            model_name="sisa_fail_verify",
        )
        is_valid = await algo.verify(context)
        assert is_valid is False

    async def test_utility_retained_after_unlearning(self):
        algo = SISAUnlearning(num_shards=4)
        context = UnlearningContext(
            target_data_ids=["data_000000", "data_000005", "data_000010"],
            data_size=100,
            model_name="sisa_utility_test",
        )
        result = await algo.unlearn(context)
        assert result.utility_retained > 0.5


@pytest.mark.asyncio
class TestInfluenceFunctionAlgorithm:
    async def test_unlearn_returns_success(self):
        algo = InfluenceFunctionUnlearning(damping=1e-2)
        context = UnlearningContext(
            target_data_ids=["data_000000"],
            data_size=100,
            model_name="inf_test",
        )
        result = await algo.unlearn(context)
        assert result.success is True
        assert result.algorithm == "InfluenceFunction"
        assert result.processing_time_ms >= 0

    async def test_unlearn_removes_target_data(self):
        algo = InfluenceFunctionUnlearning(damping=1e-2)
        context = UnlearningContext(
            target_data_ids=["data_000005"],
            data_size=100,
            model_name="inf_verify_test",
        )
        await algo.unlearn(context)
        is_valid = await algo.verify(context)
        assert is_valid is True

    async def test_verify_fails_if_not_removed(self):
        algo = InfluenceFunctionUnlearning(damping=1e-2)
        context = UnlearningContext(
            target_data_ids=["data_000000"],
            data_size=50,
            model_name="inf_fail_verify",
        )
        is_valid = await algo.verify(context)
        assert is_valid is False

    async def test_utility_retained_after_unlearning(self):
        algo = InfluenceFunctionUnlearning(damping=1e-2)
        context = UnlearningContext(
            target_data_ids=["data_000000", "data_000001"],
            data_size=100,
            model_name="inf_utility_test",
        )
        result = await algo.unlearn(context)
        assert result.utility_retained > 0.0


@pytest.mark.asyncio
class TestCertifiedRemovalAlgorithm:
    async def test_unlearn_returns_success(self):
        algo = CertifiedRemovalUnlearning(epsilon=0.5, delta=1e-3)
        context = UnlearningContext(
            target_data_ids=["data_000000"],
            data_size=100,
            model_name="cert_test",
        )
        result = await algo.unlearn(context)
        assert result.success is True
        assert result.algorithm == "CertifiedRemoval"
        assert result.processing_time_ms >= 0
        assert result.metrics["noise_scale"] > 0

    async def test_unlearn_removes_target_data(self):
        algo = CertifiedRemovalUnlearning(epsilon=0.5, delta=1e-3)
        context = UnlearningContext(
            target_data_ids=["data_000005"],
            data_size=100,
            model_name="cert_verify_test",
        )
        await algo.unlearn(context)
        is_valid = await algo.verify(context)
        assert is_valid is True

    async def test_verify_fails_if_not_removed(self):
        algo = CertifiedRemovalUnlearning(epsilon=0.5, delta=1e-3)
        context = UnlearningContext(
            target_data_ids=["data_000000"],
            data_size=50,
            model_name="cert_fail_verify",
        )
        is_valid = await algo.verify(context)
        assert is_valid is False

    async def test_different_epsilon_affects_noise_scale(self):
        algo_high = CertifiedRemovalUnlearning(epsilon=10.0, delta=1e-3)
        algo_low = CertifiedRemovalUnlearning(epsilon=0.1, delta=1e-3)
        ctx = UnlearningContext(
            target_data_ids=["data_000000"],
            data_size=100,
            model_name="cert_noise_test",
        )
        r_high = await algo_high.unlearn(ctx)
        r_low = await algo_low.unlearn(ctx)
        assert r_low.metrics["noise_scale"] > r_high.metrics["noise_scale"]

    async def test_utility_retained_after_unlearning(self):
        algo = CertifiedRemovalUnlearning(epsilon=1.0, delta=1e-3)
        context = UnlearningContext(
            target_data_ids=["data_000000", "data_000001"],
            data_size=100,
            model_name="cert_utility_test",
        )
        result = await algo.unlearn(context)
        assert result.utility_retained > 0.0
