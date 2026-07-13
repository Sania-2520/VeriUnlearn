import pytest
from unlearning.hybrid_controller import HybridAdaptiveController
from unlearning.algorithms.base import UnlearningContext


class TestHybridAdaptiveController:
    @pytest.fixture
    def controller(self):
        return HybridAdaptiveController()

    @pytest.mark.asyncio
    async def test_small_data_quick_latency(self, controller):
        context = UnlearningContext(
            target_data_ids=["1", "2"],
            data_size=50,
            latency_ms=200,
            accuracy_target=0.95,
        )
        strategies = controller.select_strategies(context)
        assert len(strategies) >= 1
        assert any(s.name == "InfluenceFunction" for s in strategies)

    @pytest.mark.asyncio
    async def test_large_data_high_accuracy(self, controller):
        context = UnlearningContext(
            target_data_ids=list(range(100)),
            data_size=5000,
            accuracy_target=0.99,
            regulatory="gdpr",
        )
        strategies = controller.select_strategies(context)
        assert len(strategies) >= 1
        names = [s.name for s in strategies]
        assert "CertifiedRemoval" in names

    @pytest.mark.asyncio
    async def test_execute_returns_result(self, controller):
        context = UnlearningContext(
            target_data_ids=["1"],
            data_size=10,
        )
        result = await controller.execute(context)
        assert result.success is True
        assert result.algorithm == "hybrid"
        assert result.processing_time_ms >= 0

    @pytest.mark.asyncio
    async def test_execute_with_multiple_strategies(self, controller):
        context = UnlearningContext(
            target_data_ids=list(range(10)),
            data_size=500,
            accuracy_target=0.99,
        )
        result = await controller.execute(context)
        assert result.success is True
        assert len(result.metrics) >= 1

    def test_deduplicate_removes_duplicates(self, controller):
        from unlearning.algorithms.sisa import SISAUnlearning
        strategies = [SISAUnlearning(), SISAUnlearning()]
        deduped = controller._deduplicate(strategies)
        assert len(deduped) == 1
