"""Demo bootstrap: `python -m app.seed`.

Downloads + ingests the Adult Census dataset (if not present), trains a SISA
model with influence scoring, and creates demo users. Safe to re-run.
"""
from __future__ import annotations

import asyncio
import logging

from app.core.logging import configure_logging, get_logger
from app.core.security import hash_password
from app.db.models import MLModel
from app.db.session import SessionLocal, init_db
from app.repositories.dataset_repo import DatasetRepository
from app.repositories.model_repo import ModelRepository
from app.repositories.user_repo import UserRepository
from app.services.audit import AuditService
from app.services.influence import InfluenceEngine
from app.services.ingestion import IngestionService
from app.services.sisa import SISAEngine

configure_logging("INFO")
logger = get_logger("veriunlearn.seed")

DEMO_USERS = [
    ("admin@veriunlearn.dev", "Admin User", "admin12345", "admin"),
    ("operator@veriunlearn.dev", "Operator User", "operator123", "operator"),
    ("auditor@veriunlearn.dev", "Auditor User", "auditor123", "auditor"),
]


async def run(limit: int | None = 8000, shard_count: int = 4) -> None:
    await init_db()
    async with SessionLocal() as session:
        audit = AuditService(session)
        await audit.log(event_type="system.seed", actor="seed")

        # Users
        users = UserRepository(session)
        for email, name, password, role in DEMO_USERS:
            if await users.get_by_email(email) is None:
                await users.create(
                    email=email, full_name=name, password_hash=hash_password(password), role=role
                )
                logger.info("Created user %s (%s)", email, role)

        # Dataset
        datasets = DatasetRepository(session)
        existing = await datasets.list(limit=5)
        dataset = next((d for d in existing if d.name == "adult-census"), None)
        if dataset is None:
            dataset = await IngestionService(session).bootstrap_adult(
                limit=limit, shard_count=shard_count
            )
            logger.info("Ingested Adult Census: %d records", dataset.record_count)
        else:
            logger.info("Adult Census already present (%d records)", dataset.record_count)

        # Model
        model = await ModelRepository(session).get_active_for_dataset(dataset.id)
        if model is None:
            model = MLModel(
                name=f"{dataset.name}-v1", model_type="linear", dataset_id=dataset.id,
                shard_count=dataset.shard_count,
            )
            model = await ModelRepository(session).add(model)
            model = await SISAEngine(session).train_model(model, dataset)
            updated = await InfluenceEngine(session).update_all_scores(model, dataset)
            logger.info("Trained model %s (influence scores: %d)", model.id, updated)
        else:
            logger.info("Model %s already trained", model.id)

        await audit.log(
            event_type="system.seed.completed",
            actor="seed",
            payload={"dataset": dataset.id, "model": model.id},
        )
        await session.commit()
        logger.info("Seed complete. Login: admin@veriunlearn.dev / admin12345")


if __name__ == "__main__":
    asyncio.run(run())
