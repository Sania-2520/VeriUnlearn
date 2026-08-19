"""Dataset ingestion.

Supported sources: CSV, JSON, JSONL, TXT, PDF (text extraction via pypdf),
plus a built-in Adult Census bootstrap.

Per record the pipeline:
  1. builds canonical JSON + SHA-256 content hash
  2. detects real identity columns (name/email/phone/aadhaar/pan/passport/dob/
     address/customer/employee ids) or synthesises a deterministic profile
  3. detects chat/conversation columns for conversation-scoped unlearning
  4. classifies sensitivity, assigns a SISA shard (stratified by label)
  5. persists the record (+ source file/page metadata, original text) and
     indexes its embedding in the vector store + embedding_index table
"""
from __future__ import annotations

import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ValidationFailedError
from app.core.security import aes_encrypt
from app.db.models import Dataset, DatasetRecord, EmbeddingIndex, IdentityIndex
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

# Columns that carry identity data rather than model features.
_IDENTITY_COLUMNS = {
    "full_name", "name", "first_name", "last_name", "email", "email_id",
    "phone", "mobile", "phone_number", "aadhaar", "aadhar", "uid", "pan",
    "passport", "passport_no", "passport_number", "dob", "date_of_birth",
    "birth_date", "address", "customer_id", "cust_id", "employee_id", "emp_id",
}
_CHAT_COLUMNS = {"chat_id", "conversation_id", "conversation", "thread_id"}


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
            urllib.request.urlretrieve(ADULT_URL, raw_path)
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

    async def ingest_file(self, filename: str, content: bytes, *, shard_count: int | None = None) -> Dataset:
        suffix = Path(filename).suffix.lower()
        if suffix == ".csv":
            return await self.ingest_csv_bytes(
                content, name=Path(filename).stem, source_type="csv",
                shard_count=shard_count or settings.DEFAULT_SHARD_COUNT, source_filename=filename,
            )
        if suffix in {".json"}:
            return await self._ingest_json_bytes(content, name=Path(filename).stem, shard_count=shard_count, source_filename=filename)
        if suffix in {".jsonl", ".ndjson"}:
            return await self._ingest_jsonl_bytes(content, name=Path(filename).stem, shard_count=shard_count, source_filename=filename)
        if suffix in {".txt", ".text"}:
            return await self._ingest_txt_bytes(content, name=Path(filename).stem, shard_count=shard_count, source_filename=filename)
        if suffix == ".pdf":
            return await self._ingest_pdf_bytes(content, name=Path(filename).stem, shard_count=shard_count, source_filename=filename)
        raise ValidationFailedError(
            f"Unsupported file type '{suffix}'. Supported: pdf, csv, json, jsonl, ndjson, txt"
        )

    async def ingest_csv_bytes(
        self,
        content: bytes,
        *,
        name: str,
        description: str | None = None,
        label_column: str | None = None,
        shard_count: int | None = None,
        source_type: str = "csv",
        source_filename: str | None = None,
    ) -> Dataset:
        try:
            df = pd.read_csv(io.BytesIO(content))
        except Exception as exc:
            raise ValidationFailedError(f"Could not parse CSV: {exc}") from exc
        return await self._ingest_dataframe(
            df, name=name, description=description, label_column=label_column, source_type=source_type,
            shard_count=shard_count or settings.DEFAULT_SHARD_COUNT, source_filename=source_filename,
        )

    async def _ingest_json_bytes(self, content: bytes, *, name: str, shard_count: int | None, source_filename: str | None) -> Dataset:
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValidationFailedError(f"Invalid JSON: {exc}") from exc
        rows = data if isinstance(data, list) else data.get("records", [data])
        return await self._ingest_dataframe(
            pd.DataFrame(rows), name=name, source_type="json",
            shard_count=shard_count or settings.DEFAULT_SHARD_COUNT, source_filename=source_filename,
        )

    async def _ingest_jsonl_bytes(self, content: bytes, *, name: str, shard_count: int | None, source_filename: str | None) -> Dataset:
        rows = []
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValidationFailedError(f"Invalid JSONL encoding: {exc}") from exc
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValidationFailedError(f"Invalid JSONL line: {exc}") from exc
        return await self._ingest_dataframe(
            pd.DataFrame(rows), name=name, source_type="jsonl",
            shard_count=shard_count or settings.DEFAULT_SHARD_COUNT, source_filename=source_filename,
        )

    async def _ingest_txt_bytes(self, content: bytes, *, name: str, shard_count: int | None, source_filename: str | None) -> Dataset:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValidationFailedError(f"File is not valid UTF-8 text: {exc}") from exc
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        df = pd.DataFrame({"text": lines})
        return await self._ingest_dataframe(
            df, name=name, source_type="txt", label_column=None,
            shard_count=shard_count or settings.DEFAULT_SHARD_COUNT, source_filename=source_filename,
        )

    async def _ingest_pdf_bytes(self, content: bytes, *, name: str, shard_count: int | None, source_filename: str | None) -> Dataset:
        """Extract per-page text from a PDF; each page becomes a knowledge chunk."""
        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("pypdf is required for PDF ingestion") from exc
        try:
            reader = PdfReader(io.BytesIO(content))
            pages = [(page.extract_text() or "").strip() for page in reader.pages]
        except Exception as exc:
            raise ValidationFailedError(f"Could not parse PDF: {exc}") from exc
        pages = [p for p in pages if p]
        if not pages:
            raise ValidationFailedError("PDF contains no extractable text")
        df = pd.DataFrame({"text": pages, "page": list(range(len(pages)))})
        dataset = await self._ingest_dataframe(
            df, name=name, source_type="pdf", label_column=None,
            shard_count=shard_count or settings.DEFAULT_SHARD_COUNT, source_filename=source_filename,
        )
        # Reassign (not in-place mutate): SQLAlchemy does not track mutations
        # of plain JSON values, so ``dataset.meta["kind"] = ...`` would never
        # be persisted to the database.
        dataset.meta = {**dataset.meta, "kind": "documents"}
        await self.session.flush()
        return dataset

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
        source_filename: str | None = None,
    ) -> Dataset:
        if df.empty:
            raise ValidationFailedError("Dataset is empty")

        # Infer label column when none declared: last categorical-looking column.
        if label_column is None:
            last = df.columns[-1]
            if df[last].nunique() <= 20 and (df[last].dtype == object or df[last].nunique() <= 10):
                label_column = last

        lower_cols = {str(c).strip().lower(): c for c in df.columns}
        identity_columns = {
            lower_cols[k] for k in _IDENTITY_COLUMNS if k in lower_cols
        }
        chat_column = next((lower_cols[k] for k in _CHAT_COLUMNS if k in lower_cols), None)
        feature_columns = [
            c for c in df.columns
            if c != label_column and c not in identity_columns and c != chat_column
        ]

        dataset = Dataset(
            name=name,
            description=description,
            source_type=source_type,
            record_count=len(df),
            feature_names=feature_columns,
            label_column=label_column,
            shard_count=shard_count,
            meta={"identity_columns": sorted(identity_columns), "chat_column": chat_column},
        )
        dataset = await self.repo.add(dataset)

        records: list[DatasetRecord] = []
        class_counters: dict[str, int] = {}
        source_ts = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC for naive column

        for index, (_, row) in enumerate(df.iterrows()):
            features: dict[str, Any] = {}
            identity_vals: dict[str, Any] = {}
            chat_id: str | None = None
            for col in feature_columns:
                value = row[col]
                features[col] = None if pd.isna(value) else (value.item() if hasattr(value, "item") else value)
            if chat_column is not None:
                chat_value = row[chat_column]
                if not pd.isna(chat_value):
                    chat_id = str(chat_value.item() if hasattr(chat_value, "item") else chat_value)
            for col in identity_columns:
                value = row[col]
                if pd.isna(value):
                    continue
                value = value.item() if hasattr(value, "item") else str(value).strip()
                identity_vals[col] = value

            label = row[label_column] if label_column else None
            if label_column and pd.isna(label):
                label = None
            elif hasattr(label, "item"):
                label = label.item()
            elif isinstance(label, str):
                label = label.strip()

            content_hash = sha256_hex(canonical_json({"features": features, "label": label}))
            identity = synthesize_identity(content_hash, existing=identity_vals or None)
            sensitivity = classify_sensitivity(features)
            original_text = json.dumps(row.to_dict(), default=str) if source_type != "txt" else str(row.get("text", ""))

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
                phone_enc=aes_encrypt(identity["phone"]),
                aadhaar_enc=aes_encrypt(identity["aadhaar"]),
                pan_enc=aes_encrypt(identity["pan"]),
                passport_enc=aes_encrypt(identity["passport"]),
                dob_enc=aes_encrypt(identity["dob"]),
                address_enc=aes_encrypt(identity["address"]),
                sensitivity=sensitivity,
                chat_id=chat_id,
                source_filename=source_filename,
                source_timestamp=source_ts,
                chunk_index=index,
                original_text=original_text,
                content_hash=content_hash,
            )
            records.append(record)

        # Batch the inserts: flush-per-record makes ingestion O(n) commits.
        self.session.add_all(records)
        await self.session.flush()
        await self._index_embeddings(dataset, records)
        await self._index_identity_profile(dataset, records)
        dataset.record_count = len(records)
        await self.session.flush()
        logger.info("Ingested dataset %s with %d records", dataset.id, len(records))
        return dataset

    # ------------------------------------------------------------------ indexing

    async def _index_embeddings(self, dataset: Dataset, records: list[DatasetRecord]) -> None:
        """Index numeric feature vectors (vector search + embedding_index table)."""
        numeric_cols = [
            c for c in dataset.feature_names
            if c in records[0].features and isinstance(records[0].features[c], (int, float))
        ]
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
        # One bulk upsert instead of a per-record round trip (~25 ms each).
        self.vectors.upsert_batch(
            collection,
            [
                (
                    record.id,
                    vec,
                    {"record_id": record.id, "identity_key": record.identity_key, "dataset_id": dataset.id},
                )
                for record, vec in zip(records, normalized)
            ],
        )
        for record, vec in zip(records, normalized):
            vector_id = record.id
            record.embedding_id = record.id
            record.vector_id = vector_id
            self.session.add(
                EmbeddingIndex(
                    record_id=record.id,
                    dataset_id=dataset.id,
                    embedding_id=record.id,
                    vector_id=vector_id,
                    chunk_id=f"chunk-{dataset.id}-{record.record_index}",
                    dim=int(vec.shape[0]),
                )
            )

    async def _index_identity_profile(self, dataset: Dataset, records: list[DatasetRecord]) -> None:
        """Merge per-record identity data into the denormalised identity_index."""
        from app.core.security import aes_decrypt

        profiles: dict[str, dict[str, Any]] = {}
        for record in records:
            key = record.identity_key
            if not key:
                continue
            profile = profiles.setdefault(
                key,
                {
                    "identity_key": key,
                    "full_name": "", "email": "", "phone": "", "aadhaar": "",
                    "pan": "", "passport": "", "customer_id": "", "employee_id": "",
                    "dob": "", "address": "", "count": 0, "dataset_ids": set(),
                },
            )
            profile["full_name"] = profile["full_name"] or aes_decrypt(record.full_name_enc)
            profile["email"] = profile["email"] or aes_decrypt(record.email_enc)
            profile["phone"] = profile["phone"] or aes_decrypt(record.phone_enc)
            profile["aadhaar"] = profile["aadhaar"] or aes_decrypt(record.aadhaar_enc)
            profile["pan"] = profile["pan"] or aes_decrypt(record.pan_enc)
            profile["passport"] = profile["passport"] or aes_decrypt(record.passport_enc)
            profile["dob"] = profile["dob"] or aes_decrypt(record.dob_enc)
            profile["address"] = profile["address"] or aes_decrypt(record.address_enc)
            profile["customer_id"] = profile["customer_id"] or str(record.features.get("customer_id") or "")
            profile["employee_id"] = profile["employee_id"] or str(record.features.get("employee_id") or "")
            profile["count"] += 1
            profile["dataset_ids"].add(dataset.id)

        for key, profile in profiles.items():
            existing = (
                await self.session.execute(
                    select(IdentityIndex).where(IdentityIndex.identity_key == key)
                )
            ).scalar_one_or_none()
            if existing is None:
                self.session.add(
                    IdentityIndex(
                        identity_key=key,
                        full_name=profile["full_name"],
                        email=profile["email"],
                        phone=profile["phone"],
                        aadhaar=profile["aadhaar"],
                        pan=profile["pan"],
                        passport=profile["passport"],
                        customer_id=profile["customer_id"],
                        employee_id=profile["employee_id"],
                        dob=profile["dob"],
                        address=profile["address"],
                        record_count=profile["count"],
                        dataset_ids=sorted(profile["dataset_ids"]),
                    )
                )
            else:
                existing.full_name = existing.full_name or profile["full_name"]
                existing.email = existing.email or profile["email"]
                existing.phone = existing.phone or profile["phone"]
                existing.aadhaar = existing.aadhaar or profile["aadhaar"]
                existing.pan = existing.pan or profile["pan"]
                existing.passport = existing.passport or profile["passport"]
                existing.dob = existing.dob or profile["dob"]
                existing.address = existing.address or profile["address"]
                existing.customer_id = existing.customer_id or profile["customer_id"]
                existing.employee_id = existing.employee_id or profile["employee_id"]
                existing.record_count += profile["count"]
                existing.dataset_ids = sorted(set(existing.dataset_ids) | profile["dataset_ids"])
