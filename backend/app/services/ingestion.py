"""Dataset ingestion.

Supported sources: CSV, JSON, JSONL, TXT (tabular/line-based), plus a built-in
Adult Census bootstrap (``adult.data`` is downloaded from the UCI mirror on
first use — the standard benchmark for the demo pipeline).

Ingestion pipeline per row:
  1. build canonical JSON + SHA-256 content hash
  2. synthesize/decrypt identity (names/emails) — deterministic
  3. classify sensitivity
  4. assign SISA shard
  5. persist record + embedding vector
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ValidationFailedError
from app.core.security import aes_encrypt
from app.db.models import Dataset, DatasetRecord
from app.repositories.dataset_repo import DatasetRepository
from app.services.crypto import canonical_json, sha256_hex
from app.services.embeddings import get_vector_store
from app.services.pii import classify_sensitivity, synthesize_identity

logger = logging.getLogger("veriunlearn.ingestion")

ADULT_COLUMNS = [
    "age", "workclass", "fnlwgt", "education", "education-num", "marital-status",
    "occupation", "relationship", "race", "sex", "capital-gain", "capital-loss",
    "hours-per-week", "native-country", "income",
]
ADULT_URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data"


class IngestionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = DatasetRepository(session)
        self.vectors = get_vector_store()

    # ------------------------------------------------------------------ adult

    async def bootstrap_adult(self, *, limit: int | None = None, shard_count: int | None = None) -> Dataset:
        """Download (once) + ingest the Adult Census dataset."""
        data_dir = Path(settings.DATA_DIR) / "adult"
        data_dir.mkdir(parents=True, exist_ok=True)
        raw_path = data_dir / "adult.data"
        if not raw_path.exists():
            import urllib.request

            logger.info("Downloading Adult Census from UCI mirror ...")
            urllib.request.urlretrieve(ADULT_URL, raw_path)  # noqa: S310 - fixed https-free mirror
        df = pd.read_csv(raw_path, header=None, names=ADULT_COLUMNS, na_values="?")
        df = df.dropna().reset_index(drop=True)
        if limit:
            df = df.head(limit)
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        return await self.ingest_csv_bytes(
            buffer.getvalue().encode("utf-8"),
            name="adult-census",
            description="UCI Adult Census (bootstrap)",
            label_column="income",
            shard_count=shard_count or settings.DEFAULT_SHARD_COUNT,
        )

    # ------------------------------------------------------------------ files

    async def ingest_csv_bytes(
        self,
        content: bytes,
        *,
        name: str,
        description: str | None = None,
        label_column: str | None = None,
        shard_count: int | None = None,
        source_type: str = "csv",
    ) -> Dataset:
        try:
            df = pd.read_csv(io.BytesIO(content))
        except Exception as exc:
            raise ValidationFailedError(f"Could not parse CSV: {exc}") from exc
        return await self._ingest_dataframe(
            df, name=name, description=description, label_column=label_column, source_type=source_type,
            shard_count=shard_count or settings.DEFAULT_SHARD_COUNT,
        )

    async def ingest_file(self, filename: str, content: bytes, *, shard_count: int | None = None) -> Dataset:
        suffix = Path(filename).suffix.lower()
        if suffix == ".csv":
            return await self.ingest_csv_bytes(
                content, name=Path(filename).stem, source_type="csv",
                shard_count=shard_count or settings.DEFAULT_SHARD_COUNT,
            )
        if suffix in {".json"}:
            return await self._ingest_json_bytes(content, name=Path(filename).stem, shard_count=shard_count)
        if suffix in {".jsonl", ".ndjson"}:
            return await self._ingest_jsonl_bytes(content, name=Path(filename).stem, shard_count=shard_count)
        if suffix in {".txt", ".text"}:
            return await self._ingest_txt_bytes(content, name=Path(filename).stem, shard_count=shard_count)
        raise ValidationFailedError(
            f"Unsupported file type '{suffix}'. Supported: csv, json, jsonl, ndjson, txt"
        )

    async def _ingest_json_bytes(self, content: bytes, *, name: str, shard_count: int | None) -> Dataset:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValidationFailedError(f"Invalid JSON: {exc}") from exc
        rows = data if isinstance(data, list) else data.get("records", [data])
        df = pd.DataFrame(rows)
        return await self._ingest_dataframe(
            df, name=name, source_type="json", shard_count=shard_count or settings.DEFAULT_SHARD_COUNT
        )

    async def _ingest_jsonl_bytes(self, content: bytes, *, name: str, shard_count: int | None) -> Dataset:
        rows = []
        for line in content.decode("utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValidationFailedError(f"Invalid JSONL line: {exc}") from exc
        return await self._ingest_dataframe(
            pd.DataFrame(rows), name=name, source_type="jsonl",
            shard_count=shard_count or settings.DEFAULT_SHARD_COUNT,
        )

    async def _ingest_txt_bytes(self, content: bytes, *, name: str, shard_count: int | None) -> Dataset:
        lines = [line.strip() for line in content.decode("utf-8").splitlines() if line.strip()]
        df = pd.DataFrame({"text": lines})
        return await self._ingest_dataframe(
            df, name=name, source_type="txt", shard_count=shard_count or settings.DEFAULT_SHARD_COUNT
        )

    # ------------------------------------------------------------------ core

    async def _ingest_dataframe(
        self,
        df: pd.DataFrame,
        *,
        name: str,
        description: str | None = None,
        label_column: str | None = None,
        source_type: str = "csv",
        shard_count: int,
    ) -> Dataset:
        if df.empty:
            raise ValidationFailedError("Dataset is empty")
        # Infer a label column when none was declared: last column when it looks
        # categorical (small cardinality or non-numeric).
        if label_column is None:
            last = df.columns[-1]
            if df[last].nunique() <= 20 and (df[last].dtype == object or df[last].nunique() <= 10):
                label_column = last
        feature_columns = [c for c in df.columns if c != label_column]
        dataset = Dataset(
            name=name,
            description=description,
            source_type=source_type,
            record_count=len(df),
            feature_names=feature_columns,
            label_column=label_column,
            shard_count=shard_count,
        )
        dataset = await self.repo.add(dataset)

        records: list[DatasetRecord] = []
        # Stratified shard assignment: round-robin within each label class so
        # every shard sees both classes (SISA requirement).
        class_counters: dict[str, int] = {}
        for index, (_, row) in enumerate(df.iterrows()):
            features: dict[str, Any] = {}
            for col in feature_columns:
                value = row[col]
                features[col] = None if pd.isna(value) else (value.item() if hasattr(value, "item") else value)
            label = row[label_column] if label_column else None
            if label_column and pd.isna(label):
                label = None
            elif hasattr(label, "item"):
                label = label.item()
            elif isinstance(label, str):
                label = label.strip()

            content_hash = sha256_hex(canonical_json({"features": features, "label": label}))
            identity = synthesize_identity(content_hash)
            sensitivity = classify_sensitivity(features)
            label_key = str(label)
            pos = class_counters.get(label_key, 0)
            class_counters[label_key] = pos + 1
            record = DatasetRecord(
                dataset_id=dataset.id,
                record_index=index,
                shard_id=pos % shard_count,
                features=features,
                label=label,
                identity_key=identity["identity_key"],
                full_name_enc=aes_encrypt(identity["full_name"]),
                email_enc=aes_encrypt(identity["email"]),
                sensitivity=sensitivity,
                content_hash=content_hash,
            )
            records.append(record)

        for record in records:
            await self.repo.add(record)
        await self._index_embeddings(dataset, records)
        dataset.record_count = len(records)
        await self.session.flush()
        logger.info("Ingested dataset %s with %d records", dataset.id, len(records))
        return dataset

    async def _index_embeddings(self, dataset: Dataset, records: list[DatasetRecord]) -> None:
        """Index numeric feature vectors for vector search (identity audit)."""
        numeric_cols = [c for c in dataset.feature_names if c in records[0].features and isinstance(records[0].features[c], (int, float))]
        if not numeric_cols:
            return
        matrix = np.array(
            [[record.features[c] for c in numeric_cols] for record in records], dtype=float
        )
        matrix = np.nan_to_num(matrix)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized = matrix / norms
        collection = f"dataset_{dataset.id}"
        for record, vec in zip(records, normalized):
            self.vectors.upsert(
                collection,
                record.id,
                vec,
                {"record_id": record.id, "identity_key": record.identity_key, "dataset_id": dataset.id},
            )
            record.embedding_id = record.id
