from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

from loguru import logger

from app.core.config import settings


class BackupService:
    def __init__(self) -> None:
        self.backup_dir = Path(settings.adapter_storage_dir) / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, name: str | None = None) -> dict[str, Any]:
        timestamp = int(time.time())
        backup_name = name or f"backup_{timestamp}"
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(parents=True, exist_ok=True)

        db_path = Path(settings.sqlite_path)
        if db_path.exists():
            shutil.copy2(db_path, backup_path / "veriunlearn.db")

        adapter_dir = Path(settings.adapter_dir)
        if adapter_dir.exists():
            adapter_backup = backup_path / "adapters"
            shutil.copytree(adapter_dir, adapter_backup, dirs_exist_ok=True)

        manifest = {
            "name": backup_name,
            "timestamp": timestamp,
            "database_size": os.path.getsize(db_path) if db_path.exists() else 0,
            "adapter_count": len(list(adapter_dir.glob("model_v*"))) if adapter_dir.exists() else 0,
        }
        with open(backup_path / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Backup created: {backup_path}")
        return manifest

    def list_backups(self) -> list[dict]:
        backups = []
        for path in sorted(self.backup_dir.iterdir(), reverse=True):
            if path.is_dir():
                manifest_path = path / "manifest.json"
                if manifest_path.exists():
                    with open(manifest_path) as f:
                        backups.append(json.load(f))
                else:
                    backups.append({
                        "name": path.name,
                        "timestamp": path.stat().st_mtime,
                    })
        return backups

    def restore_backup(self, backup_name: str) -> dict[str, Any]:
        backup_path = self.backup_dir / backup_name
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_name}")

        db_backup = backup_path / "veriunlearn.db"
        if db_backup.exists():
            db_path = Path(settings.sqlite_path)
            shutil.copy2(db_backup, db_path)

        adapter_backup = backup_path / "adapters"
        if adapter_backup.exists():
            adapter_dir = Path(settings.adapter_dir)
            if adapter_dir.exists():
                shutil.rmtree(adapter_dir)
            shutil.copytree(adapter_backup, adapter_dir)

        logger.info(f"Backup restored: {backup_name}")
        return {"status": "restored", "backup": backup_name}

    def delete_backup(self, backup_name: str) -> bool:
        backup_path = self.backup_dir / backup_name
        if not backup_path.exists():
            return False
        shutil.rmtree(backup_path)
        logger.info(f"Backup deleted: {backup_name}")
        return True
