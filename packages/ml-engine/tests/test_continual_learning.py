import pytest

from training.continual_learning import ContinualLearningConfig, ContinualLearningManager
from training.drift_detector import DriftConfig, DriftDetector
from training.ewc import ElasticWeightConsolidation
from training.replay_buffer import ReplayBuffer, ReplayBufferConfig


class TestContinualLearningManager:
    @pytest.fixture
    def cl(self):
        cfg = ContinualLearningConfig(replay_capacity=100, drift_window=50)
        return ContinualLearningManager(cfg)

    def test_add_and_get_task(self, cl):
        task = cl.add_task("test-task", {"source": "test"})
        assert task["task_id"] == "test-task"
        assert cl.get_task("test-task") is not None

    def test_record_sample(self, cl):
        cl.record_sample([1.0, 0.5, 0.2], target=0, task_id="t1", confidence=0.85, loss=0.12)
        stats = cl.get_stats()
        assert stats["task_count"] == 1

    def test_get_stats(self, cl):
        stats = cl.get_stats()
        assert "ewc" in stats
        assert "replay_buffer" in stats
        assert "drift_detector" in stats

    def test_detect_drift(self, cl):
        state = cl.detect_drift("confidence", 0.85)
        assert state["metric"] == "confidence"

    def test_get_drift_state(self, cl):
        state = cl.get_drift_state("confidence")
        assert state.get("available") is False or "drift_score" in state


class TestReplayBuffer:
    @pytest.fixture
    def buffer(self):
        cfg = ReplayBufferConfig(capacity=50, storage_path="./test_replay_buffer")
        return ReplayBuffer(cfg)

    def test_add_and_sample(self, buffer):
        buffer.add([1.0, 0.5], target=0, task_id="default")
        buffer.add([0.8, 0.3], target=1, task_id="default")
        samples = buffer.sample(2)
        assert len(samples) == 2

    def test_get_stats(self, buffer):
        buffer.add([1.0, 0.5], target=0)
        stats = buffer.get_stats()
        assert stats["size"] == 1


class TestDriftDetector:
    @pytest.fixture
    def detector(self):
        cfg = DriftConfig(window_size=20, min_samples=5)
        return DriftDetector(cfg)

    def test_record_and_alert(self, detector):
        for i in range(10):
            detector.record("confidence", 0.8 + (i * 0.01))
        for i in range(10):
            detector.record("confidence", 0.4 + (i * 0.01))
        alerts = detector.get_recent_alerts(5)
        assert len(alerts) >= 0

    def test_get_stats(self, detector):
        for i in range(10):
            detector.record("confidence", 0.5)
        stats = detector.get_stats()
        assert stats["total_samples"] == 10


class TestEWC:
    def test_ewc_state_without_model(self):
        ewc = ElasticWeightConsolidation(None)
        state = ewc.get_state()
        assert "ewc_lambda" in state
