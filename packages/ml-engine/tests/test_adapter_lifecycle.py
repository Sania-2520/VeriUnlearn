import pytest

from training.adapter_lifecycle import AdapterLifecycleManager, AdapterStatus, LifecycleConfig


class TestAdapterLifecycle:
    @pytest.fixture
    def manager(self, tmp_path):
        # Persist to a pytest-managed temp dir so tests never write to tracked
        # files in the repository (keeps the working tree clean).
        mgr = AdapterLifecycleManager(LifecycleConfig(persist_path=str(tmp_path)))
        yield mgr

    def test_register_adapter(self, manager):
        version = manager.register_adapter("test-adapter", "/path/to/adapter")
        assert version.adapter_name == "test-adapter"
        assert version.version_number == 1
        assert version.status == AdapterStatus.PENDING

    def test_multiple_versions(self, manager):
        v1 = manager.register_adapter("multi", "/path/v1")
        v2 = manager.register_adapter("multi", "/path/v2")
        assert v2.version_number == 2
        assert v2.parent_version_id == v1.version_id

    def test_activate_version(self, manager):
        manager.register_adapter("act", "/path/act")
        versions = manager._adapters["act"]
        v = versions[0]
        result = manager.activate_version("act", v.version_id)
        assert result is True
        assert v.status == AdapterStatus.ACTIVE

    def test_rollback(self, manager):
        v1 = manager.register_adapter("rb", "/path/rb1")
        v2 = manager.register_adapter("rb", "/path/rb2")
        manager.activate_version("rb", v2.version_id)
        target = manager.rollback("rb")
        assert target is not None
        assert target.version_id == v1.version_id

    def test_auto_rollback_on_errors(self, manager):
        v1 = manager.register_adapter("auto", "/path/auto1")
        v2 = manager.register_adapter("auto", "/path/auto2")
        manager.activate_version("auto", v2.version_id)
        for _ in range(manager._config.rollback_on_error_threshold):
            manager.mark_failed("auto", v2.version_id)
        active = manager.get_active_version("auto")
        assert active is not None
        assert active.version_id == v1.version_id

    def test_canary_setup_and_promote(self, manager):
        stable = manager.register_adapter("canary", "/path/stable")
        canary = manager.register_adapter("canary", "/path/canary")
        manager.setup_canary("canary", stable.version_id, canary.version_id, canary_traffic_pct=10.0)
        rule = manager.get_routing_rule("canary")
        assert rule["strategy"] == "canary"
        promoted = manager.promote_canary("canary")
        assert promoted is not None
        assert promoted.version_id == canary.version_id

    def test_list_adapters(self, manager):
        manager.register_adapter("a1", "/path/a1")
        manager.register_adapter("a2", "/path/a2")
        adapters = manager.list_adapters()
        assert len(adapters) == 2

    def test_get_versions(self, manager):
        manager.register_adapter("ver", "/path/ver1")
        manager.register_adapter("ver", "/path/ver2")
        versions = manager.get_versions("ver")
        assert len(versions) == 2

    def test_adapter_health(self, manager):
        manager.register_adapter("health", "/path/hlth")
        v = manager._adapters["health"][0]
        manager.activate_version("health", v.version_id)
        health = manager.get_adapter_health("health")
        assert health["healthy"] is True
        assert health["status"] == "active"
