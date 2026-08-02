import hashlib
import json
import logging
import os
import shutil
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from verification.merkle_tree import MerkleTree
from verification.signatures import SignatureManager

logger = logging.getLogger(__name__)


@dataclass
class ModelVersion:
    version_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    model_name: str = ""
    version_number: int = 0
    parent_version_id: Optional[str] = None
    checkpoint_path: str = ""
    adapter_path: Optional[str] = None
    algorithm: str = ""
    status: str = "training"
    config: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    training_dataset_hash: str = ""
    training_dataset_size: int = 0
    removed_data_ids: list[str] = field(default_factory=list)
    deletion_history: list[dict] = field(default_factory=list)
    sha256: str = ""
    merkle_root: str = ""
    artifact_location: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    deprecated_at: Optional[str] = None
    created_by: str = "system"
    tags: dict = field(default_factory=dict)
    gpu_hours: float = 0.0
    training_time_seconds: float = 0.0


@dataclass
class RegistryConfig:
    base_path: str = "./model_registry"
    max_versions_per_model: int = 50
    enable_merkle_chaining: bool = True
    enable_signature_verification: bool = True


class ModelRegistry:
    def __init__(self, config: RegistryConfig) -> None:
        self.config = config
        self._versions: dict[str, list[ModelVersion]] = {}
        self._current_versions: dict[str, str] = {}
        self._signature_manager = SignatureManager()
        self._initialized_paths: set[str] = set()
        self._private_key = None
        self._public_key = None
        self._public_key_path = os.path.join(config.base_path, ".signing_key.pem")
        self._ensure_directory(config.base_path)
        self._load_or_generate_signing_keys()

    def _load_or_generate_signing_keys(self) -> None:
        key_file = os.path.join(self.config.base_path, ".signing_key.json")
        if os.path.exists(key_file):
            with open(key_file, "r") as f:
                key_data = json.load(f)
            self._private_key = self._signature_manager.load_private_key(key_data["private_key"])
            self._public_key = self._signature_manager.load_public_key(key_data["public_key"])
        else:
            self._private_key, self._public_key = self._signature_manager.generate_key_pair()
            key_data = {
                "private_key": self._signature_manager.serialize_private_key(self._private_key),
                "public_key": self._signature_manager.serialize_public_key(self._public_key),
            }
            with open(key_file, "w") as f:
                json.dump(key_data, f)
            os.chmod(key_file, 0o600)

    def register_version(
        self,
        model_name: str,
        checkpoint_path: str,
        config: dict,
        metrics: dict,
        algorithm: str,
        parent_version_id: Optional[str] = None,
        removed_data_ids: Optional[list[str]] = None,
        adapter_path: Optional[str] = None,
        training_dataset_hash: str = "",
        training_dataset_size: int = 0,
        created_by: str = "system",
        tags: Optional[dict] = None,
        gpu_hours: float = 0.0,
        training_time_seconds: float = 0.0,
    ) -> ModelVersion:
        self._ensure_directory(self.config.base_path)

        if model_name not in self._versions:
            self._versions[model_name] = []
            self._load_metadata(model_name)

        existing_versions = self._versions[model_name]
        version_number = len(existing_versions) + 1

        parent_merkle_root = ""
        parent_deletion_history: list[dict] = []
        if parent_version_id:
            parent = self.get_version(model_name, parent_version_id)
            if parent is None:
                raise ValueError(f"Parent version {parent_version_id} not found")
            parent_merkle_root = parent.merkle_root
            parent_deletion_history = list(parent.deletion_history)

        version_dir = os.path.join(self.config.base_path, model_name, f"version_{version_number}")
        self._ensure_directory(version_dir)

        hash_target = adapter_path if adapter_path else checkpoint_path
        if adapter_path:
            dest_adapter = os.path.join(version_dir, "adapter")
            self._ensure_directory(dest_adapter)
            if os.path.isdir(adapter_path):
                shutil.copytree(adapter_path, dest_adapter, dirs_exist_ok=True)
            else:
                shutil.copy2(adapter_path, dest_adapter)
            final_adapter_path = dest_adapter
        else:
            final_adapter_path = None

        dest_checkpoint = os.path.join(version_dir, "checkpoint")
        if os.path.isdir(checkpoint_path):
            self._ensure_directory(dest_checkpoint)
            shutil.copytree(checkpoint_path, dest_checkpoint, dirs_exist_ok=True)
        else:
            self._ensure_directory(dest_checkpoint)
            shutil.copy2(checkpoint_path, dest_checkpoint)
        final_checkpoint_path = dest_checkpoint

        target_for_hash = final_adapter_path if adapter_path else final_checkpoint_path
        if os.path.isdir(target_for_hash):
            sha256_hash = self._compute_sha256_dir(target_for_hash)
        else:
            sha256_hash = self._compute_sha256_file(target_for_hash)

        merkle_root = ""
        registered_at = datetime.now(timezone.utc).isoformat()
        if self.config.enable_merkle_chaining:
            tree = MerkleTree()
            version_data = json.dumps({
                "version_number": version_number,
                "model_name": model_name,
                "sha256": sha256_hash,
                "algorithm": algorithm,
                "timestamp": registered_at,
            }, sort_keys=True)
            if parent_merkle_root:
                tree.add_leaf(parent_merkle_root)
            tree.add_leaf(version_data)
            merkle_root = tree.build_tree()

        signature = ""
        if self.config.enable_signature_verification and self._private_key:
            signature = self._signature_manager.sign(merkle_root, self._private_key)

        deletion_history = list(parent_deletion_history)
        if removed_data_ids:
            deletion_record = {
                "removed_data_ids": removed_data_ids,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version_number": version_number,
                "algorithm": algorithm,
            }
            deletion_history.append(deletion_record)

        model_version = ModelVersion(
            model_name=model_name,
            version_number=version_number,
            parent_version_id=parent_version_id,
            checkpoint_path=final_checkpoint_path,
            adapter_path=final_adapter_path,
            algorithm=algorithm,
            status="active",
            config=config,
            metrics=metrics,
            training_dataset_hash=training_dataset_hash,
            training_dataset_size=training_dataset_size,
            removed_data_ids=removed_data_ids or [],
            deletion_history=deletion_history,
            sha256=sha256_hash,
            merkle_root=merkle_root,
            artifact_location=version_dir,
            created_at=registered_at,
            created_by=created_by,
            tags=tags or {},
            gpu_hours=gpu_hours,
            training_time_seconds=training_time_seconds,
        )

        if signature:
            model_version.tags["_signature"] = signature

        if self._current_versions.get(model_name):
            prev_id = self._current_versions[model_name]
            prev = self.get_version(model_name, prev_id)
            if prev and prev.status == "active":
                prev.status = "deprecated"
                prev.deprecated_at = datetime.now(timezone.utc).isoformat()

        self._versions[model_name].append(model_version)
        self._current_versions[model_name] = model_version.version_id

        self._persist_metadata(model_name)
        return model_version

    def get_version(self, model_name: str, version_id: str) -> Optional[ModelVersion]:
        if model_name not in self._versions:
            self._load_metadata(model_name)
        for v in self._versions.get(model_name, []):
            if v.version_id == version_id:
                return v
        return None

    def get_latest_version(self, model_name: str) -> Optional[ModelVersion]:
        if model_name not in self._current_versions:
            self._load_metadata(model_name)
        vid = self._current_versions.get(model_name)
        if vid:
            return self.get_version(model_name, vid)
        versions = self._versions.get(model_name, [])
        if versions:
            return versions[-1]
        return None

    def list_versions(self, model_name: str, status: Optional[str] = None) -> list[ModelVersion]:
        if model_name not in self._versions:
            self._load_metadata(model_name)
        versions = self._versions.get(model_name, [])
        if status:
            return [v for v in versions if v.status == status]
        return list(versions)

    def deprecate_version(self, model_name: str, version_id: str) -> bool:
        version = self.get_version(model_name, version_id)
        if version is None:
            return False
        if version.status == "deprecated":
            return True
        version.status = "deprecated"
        version.deprecated_at = datetime.now(timezone.utc).isoformat()
        if self._current_versions.get(model_name) == version_id:
            self._current_versions.pop(model_name, None)
        self._persist_metadata(model_name)
        return True

    def rollback(self, model_name: str, target_version_id: str) -> Optional[ModelVersion]:
        target = self.get_version(model_name, target_version_id)
        if target is None:
            return None

        current = self.get_latest_version(model_name)
        current_version_id = current.version_id if current else None

        rollback_config = dict(target.config)
        rollback_config["_rollback_from"] = target_version_id
        rollback_config["_rollback_parent"] = current_version_id

        new_version = self.register_version(
            model_name=model_name,
            checkpoint_path=target.checkpoint_path,
            config=rollback_config,
            metrics=target.metrics,
            algorithm=target.algorithm,
            parent_version_id=current_version_id,
            removed_data_ids=[],
            adapter_path=target.adapter_path,
            training_dataset_hash=target.training_dataset_hash,
            training_dataset_size=target.training_dataset_size,
            created_by="rollback",
            tags={"_rollback": True, "_rollback_source": target_version_id},
            gpu_hours=0,
            training_time_seconds=0,
        )

        new_version.status = "active"
        self._current_versions[model_name] = new_version.version_id

        if current:
            current.status = "deprecated"
            current.deprecated_at = datetime.now(timezone.utc).isoformat()

        rollback_record = {
            "action": "rollback",
            "from_version": current_version_id,
            "to_version": target_version_id,
            "new_version": new_version.version_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        new_version.deletion_history.append(rollback_record)

        self._persist_metadata(model_name)
        return new_version

    def verify_version_integrity(self, model_name: str, version_id: str) -> dict:
        result = {
            "valid": False,
            "sha256_match": False,
            "merkle_valid": False,
            "signature_valid": False,
            "details": "",
        }

        version = self.get_version(model_name, version_id)
        if version is None:
            result["details"] = f"Version {version_id} not found"
            return result

        target_path = version.adapter_path if version.adapter_path else version.checkpoint_path
        if os.path.isdir(target_path):
            computed_hash = self._compute_sha256_dir(target_path)
        elif os.path.isfile(target_path):
            computed_hash = self._compute_sha256_file(target_path)
        else:
            result["details"] = f"Artifact path does not exist: {target_path}"
            return result

        result["sha256_match"] = computed_hash == version.sha256

        if self.config.enable_merkle_chaining and version.merkle_root:
            merkle_valid = self._verify_merkle_chain(version)
            result["merkle_valid"] = merkle_valid
        else:
            result["merkle_valid"] = True

        if self.config.enable_signature_verification:
            sig = version.tags.get("_signature", "")
            if sig and self._public_key:
                try:
                    sig_valid = self._signature_manager.verify(
                        version.merkle_root, sig, self._public_key
                    )
                    result["signature_valid"] = sig_valid
                except Exception:
                    logger.warning("Model signature validation failed")
                    result["signature_valid"] = False
            else:
                result["signature_valid"] = not self.config.enable_signature_verification
        else:
            result["signature_valid"] = True

        result["valid"] = (
            result["sha256_match"]
            and result["merkle_valid"]
            and result["signature_valid"]
        )

        if result["valid"]:
            result["details"] = "All integrity checks passed"
        else:
            failures = []
            if not result["sha256_match"]:
                failures.append("SHA256 mismatch")
            if not result["merkle_valid"]:
                failures.append("Merkle chain invalid")
            if not result["signature_valid"]:
                failures.append("Signature invalid")
            result["details"] = "; ".join(failures)

        return result

    def _verify_merkle_chain(self, version: ModelVersion) -> bool:
        if not version.parent_version_id:
            version_data = json.dumps({
                "version_number": version.version_number,
                "model_name": version.model_name,
                "sha256": version.sha256,
                "algorithm": version.algorithm,
                "timestamp": version.created_at,
            }, sort_keys=True)
            tree = MerkleTree()
            tree.add_leaf(version_data)
            return tree.build_tree() == version.merkle_root

        parent = self.get_version(version.model_name, version.parent_version_id)
        if parent is None:
            return False

        version_data = json.dumps({
            "version_number": version.version_number,
            "model_name": version.model_name,
            "sha256": version.sha256,
            "algorithm": version.algorithm,
            "timestamp": version.created_at,
        }, sort_keys=True)

        tree = MerkleTree()
        tree.add_leaf(parent.merkle_root)
        tree.add_leaf(version_data)
        computed_root = tree.build_tree()
        return computed_root == version.merkle_root

    def compare_versions(self, model_name: str, version_a: str, version_b: str) -> dict:
        va = self.get_version(model_name, version_a)
        vb = self.get_version(model_name, version_b)
        if va is None or vb is None:
            return {"error": "One or both versions not found"}

        metric_diff = {}
        all_keys = set(list(va.metrics.keys()) + list(vb.metrics.keys()))
        for k in all_keys:
            va_val = va.metrics.get(k)
            vb_val = vb.metrics.get(k)
            if va_val != vb_val:
                metric_diff[k] = {"version_a": va_val, "version_b": vb_val}

        config_diff = {}
        all_config_keys = set(list(va.config.keys()) + list(vb.config.keys()))
        for k in all_config_keys:
            va_val = va.config.get(k)
            vb_val = vb.config.get(k)
            if va_val != vb_val:
                config_diff[k] = {"version_a": va_val, "version_b": vb_val}

        return {
            "model_name": model_name,
            "version_a": {
                "version_id": va.version_id,
                "version_number": va.version_number,
                "algorithm": va.algorithm,
                "sha256": va.sha256,
                "training_dataset_size": va.training_dataset_size,
                "created_at": va.created_at,
                "status": va.status,
                "gpu_hours": va.gpu_hours,
                "training_time_seconds": va.training_time_seconds,
            },
            "version_b": {
                "version_id": vb.version_id,
                "version_number": vb.version_number,
                "algorithm": vb.algorithm,
                "sha256": vb.sha256,
                "training_dataset_size": vb.training_dataset_size,
                "created_at": vb.created_at,
                "status": vb.status,
                "gpu_hours": vb.gpu_hours,
                "training_time_seconds": vb.training_time_seconds,
            },
            "metric_diff": metric_diff,
            "config_diff": config_diff,
            "weights_identical": va.sha256 == vb.sha256,
            "data_size_diff": vb.training_dataset_size - va.training_dataset_size,
            "same_algorithm": va.algorithm == vb.algorithm,
        }

    def get_deletion_history(self, model_name: str) -> list[dict]:
        versions = self.list_versions(model_name)
        all_history: list[dict] = []
        seen: set[str] = set()
        for v in versions:
            for record in v.deletion_history:
                record_key = json.dumps(record, sort_keys=True)
                if record_key not in seen:
                    seen.add(record_key)
                    all_history.append(record)
        return all_history

    def export_version(self, model_name: str, version_id: str, export_path: str) -> str:
        version = self.get_version(model_name, version_id)
        if version is None:
            raise ValueError(f"Version {version_id} not found for model {model_name}")

        self._ensure_directory(export_path)

        dest = os.path.join(export_path, f"{model_name}_v{version.version_number}")
        self._ensure_directory(dest)

        if os.path.isdir(version.checkpoint_path):
            shutil.copytree(version.checkpoint_path, os.path.join(dest, "checkpoint"), dirs_exist_ok=True)
        else:
            self._ensure_directory(dest)
            shutil.copy2(version.checkpoint_path, os.path.join(dest, "checkpoint"))

        if version.adapter_path:
            adapter_dest = os.path.join(dest, "adapter")
            if os.path.isdir(version.adapter_path):
                shutil.copytree(version.adapter_path, adapter_dest, dirs_exist_ok=True)
            else:
                self._ensure_directory(dest)
                shutil.copy2(version.adapter_path, adapter_dest)

        metadata = {k: v for k, v in asdict(version).items() if k != "_signature"}
        metadata_path = os.path.join(dest, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)

        return dest

    def cleanup(self, keep_latest_n: int = 10) -> int:
        removed_count = 0
        for model_name in list(self._versions.keys()):
            versions = self._versions[model_name]
            deprecated = [v for v in versions if v.status == "deprecated"]

            if len(deprecated) <= keep_latest_n:
                continue

            to_remove = deprecated[: len(deprecated) - keep_latest_n]
            remove_ids = {v.version_id for v in to_remove}

            for v in to_remove:
                if os.path.isdir(v.artifact_location):
                    shutil.rmtree(v.artifact_location, ignore_errors=True)

            self._versions[model_name] = [
                v for v in versions if v.version_id not in remove_ids
            ]
            removed_count += len(to_remove)

            if self._current_versions.get(model_name) in remove_ids:
                self._current_versions.pop(model_name, None)
                remaining = self._versions[model_name]
                if remaining:
                    self._current_versions[model_name] = remaining[-1].version_id

            self._persist_metadata(model_name)

        return removed_count

    def get_registry_stats(self) -> dict:
        total_models = len(self._versions)
        total_versions = sum(len(v) for v in self._versions.values())
        total_disk_bytes = 0

        for model_name, versions in self._versions.items():
            for v in versions:
                if os.path.isdir(v.artifact_location):
                    for dirpath, dirnames, filenames in os.walk(v.artifact_location):
                        for filename in filenames:
                            filepath = os.path.join(dirpath, filename)
                            try:
                                total_disk_bytes += os.path.getsize(filepath)
                            except OSError:
                                logger.debug("Could not stat file %s", filepath, exc_info=True)

        total_disk_gb = round(total_disk_bytes / (1024 ** 3), 4)

        status_counts: dict[str, int] = {}
        algorithm_counts: dict[str, int] = {}
        for versions in self._versions.values():
            for v in versions:
                status_counts[v.status] = status_counts.get(v.status, 0) + 1
                algorithm_counts[v.algorithm] = algorithm_counts.get(v.algorithm, 0) + 1

        return {
            "total_models": total_models,
            "total_versions": total_versions,
            "total_disk_bytes": total_disk_bytes,
            "total_disk_gb": total_disk_gb,
            "status_distribution": status_counts,
            "algorithm_distribution": algorithm_counts,
            "models": {
                name: {
                    "version_count": len(versions),
                    "latest_version_id": self._current_versions.get(name, ""),
                }
                for name, versions in self._versions.items()
            },
        }

    def _persist_metadata(self, model_name: str) -> None:
        model_dir = os.path.join(self.config.base_path, model_name)
        self._ensure_directory(model_dir)
        metadata_path = os.path.join(model_dir, "registry_metadata.json")

        versions = self._versions.get(model_name, [])
        current_id = self._current_versions.get(model_name, "")

        data = {
            "model_name": model_name,
            "current_version_id": current_id,
            "versions": [asdict(v) for v in versions],
        }

        with open(metadata_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _load_metadata(self, model_name: str) -> None:
        metadata_path = os.path.join(self.config.base_path, model_name, "registry_metadata.json")
        if not os.path.exists(metadata_path):
            self._versions.setdefault(model_name, [])
            return

        with open(metadata_path, "r") as f:
            data = json.load(f)

        versions = [ModelVersion(**v) for v in data.get("versions", [])]
        self._versions[model_name] = versions
        if data.get("current_version_id"):
            self._current_versions[model_name] = data["current_version_id"]

    def _compute_sha256_file(self, path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _compute_sha256_dir(self, path: str) -> str:
        file_hashes: list[str] = []
        for root, _, files in os.walk(path):
            for filename in sorted(files):
                filepath = os.path.join(root, filename)
                rel = os.path.relpath(filepath, path)
                file_hashes.append(f"{rel}:{self._compute_sha256_file(filepath)}")

        combined = "".join(file_hashes)
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def _ensure_directory(self, path: str) -> None:
        if path not in self._initialized_paths:
            os.makedirs(path, exist_ok=True)
            self._initialized_paths.add(path)
