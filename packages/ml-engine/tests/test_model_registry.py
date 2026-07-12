import json
import os
import tempfile

import pytest

from training.model_registry import (
    ModelVersion,
    RegistryConfig,
    ModelRegistry,
)


class TestModelVersion:
    def test_version_creation_defaults(self):
        v = ModelVersion()
        assert v.version_id  # UUID generated
        assert v.model_name == ""
        assert v.version_number == 0
        assert v.status == "training"
        assert v.sha256 == ""
        assert v.merkle_root == ""
        assert v.created_at is not None
        assert v.deprecated_at is None
        assert v.config == {}
        assert v.metrics == {}
        assert v.removed_data_ids == []
        assert v.deletion_history == []
        assert v.tags == {}

    def test_version_creation_explicit(self):
        v = ModelVersion(
            version_id="v1",
            model_name="test-model",
            version_number=1,
            algorithm="hybrid",
            status="active",
            config={"lr": 0.001},
            metrics={"accuracy": 0.95},
        )
        assert v.model_name == "test-model"
        assert v.version_number == 1
        assert v.algorithm == "hybrid"
        assert v.status == "active"
        assert v.config["lr"] == 0.001
        assert v.metrics["accuracy"] == 0.95

    def test_version_unique_ids(self):
        a = ModelVersion()
        b = ModelVersion()
        assert a.version_id != b.version_id


class TestRegistryConfig:
    def test_defaults(self):
        c = RegistryConfig()
        assert c.base_path == "./model_registry"
        assert c.max_versions_per_model == 50
        assert c.enable_merkle_chaining is True
        assert c.enable_signature_verification is True

    def test_custom(self):
        c = RegistryConfig(
            base_path="/tmp/reg",
            max_versions_per_model=10,
            enable_merkle_chaining=False,
        )
        assert c.base_path == "/tmp/reg"
        assert c.max_versions_per_model == 10
        assert c.enable_merkle_chaining is False


class TestModelRegistry:
    @pytest.fixture
    def registry(self, tmp_path):
        config = RegistryConfig(base_path=str(tmp_path / "registry"))
        return ModelRegistry(config)

    def test_init_creates_directory(self, tmp_path):
        reg_path = tmp_path / "my_registry"
        config = RegistryConfig(base_path=str(reg_path))
        registry = ModelRegistry(config)
        assert reg_path.exists()
        assert registry.config == config

    def test_signing_key_generated(self, tmp_path, registry):
        assert registry._private_key is not None
        assert registry._public_key is not None

    def test_register_version(self, registry, tmp_path):
        checkpoint = tmp_path / "model.pt"
        checkpoint.write_bytes(b"fake model data")
        version = registry.register_version(
            model_name="test-model",
            checkpoint_path=str(checkpoint),
            config={"lr": 0.001},
            metrics={"accuracy": 0.95},
            algorithm="hybrid",
        )
        assert version.model_name == "test-model"
        assert version.version_number == 1
        assert version.sha256
        assert version.status == "active"
        assert version.merkle_root

    def test_register_multiple_versions(self, registry, tmp_path):
        for i in range(3):
            cp = tmp_path / f"model_{i}.pt"
            cp.write_bytes(f"data_{i}".encode())
            registry.register_version(
                model_name="multi-model",
                checkpoint_path=str(cp),
                config={},
                metrics={"step": i},
                algorithm="sisa",
            )
        versions = registry.list_versions("multi-model")
        assert len(versions) == 3
        assert versions[0].version_number == 1
        assert versions[2].version_number == 3

    def test_get_latest_version(self, registry, tmp_path):
        for i in range(3):
            cp = tmp_path / f"m_{i}.pt"
            cp.write_bytes(f"v{i}".encode())
            registry.register_version(
                model_name="latest-model",
                checkpoint_path=str(cp),
                config={},
                metrics={},
                algorithm="test",
            )
        latest = registry.get_latest_version("latest-model")
        assert latest is not None
        assert latest.version_number == 3

    def test_get_latest_version_nonexistent(self, registry):
        result = registry.get_latest_version("no-such-model")
        assert result is None

    def test_get_version(self, registry, tmp_path):
        cp = tmp_path / "model.pt"
        cp.write_bytes(b"data")
        v = registry.register_version(
            model_name="get-model",
            checkpoint_path=str(cp),
            config={},
            metrics={},
            algorithm="test",
        )
        found = registry.get_version("get-model", v.version_id)
        assert found is not None
        assert found.version_id == v.version_id

    def test_get_version_not_found(self, registry):
        result = registry.get_version("x", "nonexistent-id")
        assert result is None

    def test_deprecation(self, registry, tmp_path):
        cp = tmp_path / "model.pt"
        cp.write_bytes(b"data")
        v = registry.register_version(
            model_name="dep-model",
            checkpoint_path=str(cp),
            config={},
            metrics={},
            algorithm="test",
        )
        ok = registry.deprecate_version("dep-model", v.version_id)
        assert ok is True
        updated = registry.get_version("dep-model", v.version_id)
        assert updated.status == "deprecated"
        assert updated.deprecated_at is not None

    def test_deprecate_already_deprecated(self, registry, tmp_path):
        cp = tmp_path / "model.pt"
        cp.write_bytes(b"data")
        v = registry.register_version(
            model_name="dep2",
            checkpoint_path=str(cp),
            config={},
            metrics={},
            algorithm="test",
        )
        registry.deprecate_version("dep2", v.version_id)
        ok = registry.deprecate_version("dep2", v.version_id)
        assert ok is True

    def test_deprecate_nonexistent(self, registry):
        result = registry.deprecate_version("x", "y")
        assert result is False

    def test_rollback(self, registry, tmp_path):
        cp1 = tmp_path / "v1.pt"
        cp1.write_bytes(b"version1")
        v1 = registry.register_version(
            model_name="rb-model",
            checkpoint_path=str(cp1),
            config={"lr": 0.01},
            metrics={"acc": 0.8},
            algorithm="sisa",
        )
        cp2 = tmp_path / "v2.pt"
        cp2.write_bytes(b"version2")
        v2 = registry.register_version(
            model_name="rb-model",
            checkpoint_path=str(cp2),
            config={"lr": 0.02},
            metrics={"acc": 0.85},
            algorithm="sisa",
        )
        rolled = registry.rollback("rb-model", v1.version_id)
        assert rolled is not None
        assert rolled.status == "active"
        assert rolled.tags.get("_rollback") is True
        latest = registry.get_latest_version("rb-model")
        assert latest.version_id == rolled.version_id

    def test_rollback_nonexistent_version(self, registry):
        result = registry.rollback("x", "nonexistent")
        assert result is None

    def test_verify_integrity(self, registry, tmp_path):
        cp = tmp_path / "model.pt"
        cp.write_bytes(b"integrity data")
        v = registry.register_version(
            model_name="verify-model",
            checkpoint_path=str(cp),
            config={},
            metrics={},
            algorithm="test",
        )
        result = registry.verify_version_integrity("verify-model", v.version_id)
        assert result["valid"] is True
        assert result["sha256_match"] is True
        assert result["merkle_valid"] is True
        assert result["signature_valid"] is True

    def test_verify_integrity_nonexistent_version(self, registry):
        result = registry.verify_integrity("x", "y") if hasattr(registry, 'verify_integrity') else registry.verify_version_integrity("x", "y")
        assert result["valid"] is False

    def test_compare_versions(self, registry, tmp_path):
        cp1 = tmp_path / "a.pt"
        cp1.write_bytes(b"aaa")
        v1 = registry.register_version(
            model_name="cmp-model",
            checkpoint_path=str(cp1),
            config={"lr": 0.01},
            metrics={"acc": 0.8},
            algorithm="sisa",
        )
        cp2 = tmp_path / "b.pt"
        cp2.write_bytes(b"bbb")
        v2 = registry.register_version(
            model_name="cmp-model",
            checkpoint_path=str(cp2),
            config={"lr": 0.02},
            metrics={"acc": 0.9},
            algorithm="influence",
        )
        diff = registry.compare_versions("cmp-model", v1.version_id, v2.version_id)
        assert "metric_diff" in diff
        assert "config_diff" in diff
        assert diff["weights_identical"] is False
        assert diff["same_algorithm"] is False
        assert diff["data_size_diff"] == 0

    def test_compare_versions_nonexistent(self, registry):
        result = registry.compare_versions("x", "a", "b")
        assert "error" in result

    def test_deletion_history(self, registry, tmp_path):
        cp = tmp_path / "model.pt"
        cp.write_bytes(b"data")
        v = registry.register_version(
            model_name="dh-model",
            checkpoint_path=str(cp),
            config={},
            metrics={},
            algorithm="sisa",
            removed_data_ids=["d1", "d2"],
        )
        history = registry.get_deletion_history("dh-model")
        assert len(history) >= 1
        assert history[0]["removed_data_ids"] == ["d1", "d2"]

    def test_registry_stats(self, registry, tmp_path):
        cp = tmp_path / "model.pt"
        cp.write_bytes(b"stats data")
        registry.register_version(
            model_name="stats-model",
            checkpoint_path=str(cp),
            config={},
            metrics={},
            algorithm="sisa",
        )
        stats = registry.get_registry_stats()
        assert stats["total_models"] == 1
        assert stats["total_versions"] == 1
        assert "status_distribution" in stats
        assert "algorithm_distribution" in stats
        assert "models" in stats

    def test_export_version(self, registry, tmp_path):
        cp = tmp_path / "model.pt"
        cp.write_bytes(b"export data")
        v = registry.register_version(
            model_name="export-model",
            checkpoint_path=str(cp),
            config={},
            metrics={},
            algorithm="test",
        )
        export_path = tmp_path / "exported"
        result = registry.export_version("export-model", v.version_id, str(export_path))
        assert os.path.isdir(result)
        metadata_file = os.path.join(result, "metadata.json")
        assert os.path.exists(metadata_file)

    def test_export_nonexistent_version_raises(self, registry, tmp_path):
        with pytest.raises(ValueError):
            registry.export_version("x", "y", str(tmp_path / "ex"))

    def test_persist_and_reload(self, tmp_path):
        reg_path = tmp_path / "persist_reg"
        config = RegistryConfig(base_path=str(reg_path))

        reg1 = ModelRegistry(config)
        cp = tmp_path / "model.pt"
        cp.write_bytes(b"persist data")
        v = reg1.register_version(
            model_name="persist-model",
            checkpoint_path=str(cp),
            config={"key": "val"},
            metrics={"m": 1.0},
            algorithm="test",
        )

        reg2 = ModelRegistry(config)
        found = reg2.get_version("persist-model", v.version_id)
        assert found is not None
        assert found.model_name == "persist-model"
        assert found.config["key"] == "val"

    def test_list_versions_with_status_filter(self, registry, tmp_path):
        cp = tmp_path / "model.pt"
        cp.write_bytes(b"data")
        v = registry.register_version(
            model_name="filter-model",
            checkpoint_path=str(cp),
            config={},
            metrics={},
            algorithm="test",
        )
        all_versions = registry.list_versions("filter-model")
        assert len(all_versions) == 1
        active = registry.list_versions("filter-model", status="active")
        assert len(active) == 1
        deprecated = registry.list_versions("filter-model", status="deprecated")
        assert len(deprecated) == 0

    def test_signature_key_persistence(self, tmp_path):
        reg_path = tmp_path / "sig_reg"
        config = RegistryConfig(base_path=str(reg_path))
        reg1 = ModelRegistry(config)
        pk1 = reg1._private_key

        reg2 = ModelRegistry(config)
        assert reg2._private_key is not None
        priv1 = reg1._signature_manager.serialize_private_key(pk1)
        priv2 = reg2._signature_manager.serialize_private_key(reg2._private_key)
        assert priv1 == priv2
