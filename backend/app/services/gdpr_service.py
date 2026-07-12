from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message
from app.models.document import Document, DocumentChunk
from app.models.training import TrainingSample, ModelVersion
from app.models.unlearning import UnlearningRequest, AuditLedger
from app.models.user import User


class GDPRService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def export_user_data(self, user: User) -> dict[str, Any]:
        export: dict[str, Any] = {
            "export_version": "1.0",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "created_at": str(user.created_at) if user.created_at else None,
            },
            "conversations": [],
            "training_samples": [],
            "documents": [],
            "unlearning_requests": [],
            "audit_entries": [],
        }

        conv_result = await self.db.execute(
            select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.created_at)
        )
        conversations = conv_result.scalars().all()
        for conv in conversations:
            msg_result = await self.db.execute(
                select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at)
            )
            messages = msg_result.scalars().all()
            export["conversations"].append({
                "id": conv.id,
                "title": conv.title,
                "is_active": conv.is_active,
                "created_at": str(conv.created_at) if conv.created_at else None,
                "messages": [
                    {
                        "id": m.id,
                        "role": m.role,
                        "content": m.content,
                        "tokens": m.tokens,
                        "created_at": str(m.created_at) if m.created_at else None,
                    }
                    for m in messages
                ],
            })

        sample_result = await self.db.execute(
            select(TrainingSample).where(TrainingSample.user_id == user.id).order_by(TrainingSample.created_at)
        )
        samples = sample_result.scalars().all()
        for s in samples:
            export["training_samples"].append({
                "id": s.id,
                "conversation_id": s.conversation_id,
                "content": s.content,
                "user_prompt": s.user_prompt,
                "shard_id": s.shard_id,
                "version": s.version,
                "created_at": str(s.created_at) if s.created_at else None,
            })

        doc_result = await self.db.execute(
            select(Document).where(Document.user_id == user.id).order_by(Document.created_at)
        )
        documents = doc_result.scalars().all()
        for doc in documents:
            export["documents"].append({
                "id": doc.id,
                "filename": doc.filename,
                "content_type": doc.content_type,
                "size_bytes": doc.size_bytes,
                "status": doc.status,
                "created_at": str(doc.created_at) if doc.created_at else None,
            })

        unlearn_result = await self.db.execute(
            select(UnlearningRequest).where(UnlearningRequest.user_id == user.id).order_by(UnlearningRequest.created_at)
        )
        unlearning_requests = unlearn_result.scalars().all()
        for req in unlearning_requests:
            result_data = None
            if req.result:
                result_data = {
                    "algorithm": req.result.algorithm,
                    "privacy_score": req.result.privacy_score,
                    "merkle_root": req.result.merkle_root,
                    "signature": req.result.signature,
                    "certificate_hash": req.result.certificate_hash,
                }
            export["unlearning_requests"].append({
                "id": req.id,
                "algorithm": req.algorithm,
                "reason": req.reason,
                "status": req.status,
                "progress": req.progress,
                "created_at": str(req.created_at) if req.created_at else None,
                "result": result_data,
            })

        audit_result = await self.db.execute(
            select(AuditLedger).where(AuditLedger.user_id == user.id).order_by(AuditLedger.created_at)
        )
        audit_entries = audit_result.scalars().all()
        for entry in audit_entries:
            export["audit_entries"].append({
                "id": entry.id,
                "event_type": entry.event_type,
                "event_data": entry.event_data,
                "ip_address": entry.ip_address,
                "created_at": str(entry.created_at) if entry.created_at else None,
            })

        return export

    async def delete_user_account(self, user: User) -> dict[str, Any]:
        deleted: dict[str, Any] = {
            "conversations": 0,
            "messages": 0,
            "training_samples": 0,
            "documents": 0,
            "document_files": 0,
            "vectors": 0,
            "model_adapters": 0,
            "unlearning_requests": 0,
            "audit_entries": 0,
            "user": False,
        }

        doc_result = await self.db.execute(
            select(Document).where(Document.user_id == user.id)
        )
        documents = doc_result.scalars().all()
        for doc in documents:
            if os.path.exists(doc.storage_path):
                try:
                    os.remove(doc.storage_path)
                    deleted["document_files"] += 1
                except OSError as e:
                    logger.warning(f"Failed to delete document file {doc.storage_path}: {e}")

            chunk_result = await self.db.execute(
                select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
            )
            chunks = chunk_result.scalars().all()
            for chunk in chunks:
                if chunk.embedding_id:
                    try:
                        from app.services.rag_service import RAGService
                        rag = RAGService(self.db)
                        await rag.delete_point(chunk.embedding_id)
                        deleted["vectors"] += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete vector {chunk.embedding_id}: {e}")
            deleted["documents"] += 1

        sample_result = await self.db.execute(
            select(TrainingSample).where(TrainingSample.user_id == user.id)
        )
        samples = sample_result.scalars().all()
        deleted["training_samples"] = len(samples)

        version_result = await self.db.execute(
            select(ModelVersion).join(TrainingSample, ModelVersion.dataset_id == TrainingSample.dataset_id)
            .where(TrainingSample.user_id == user.id)
            .distinct()
        )
        versions = version_result.scalars().all()
        for v in versions:
            adapter_path = Path(v.adapter_path)
            if adapter_path.exists() and adapter_path.is_dir():
                try:
                    shutil.rmtree(adapter_path)
                    deleted["model_adapters"] += 1
                except OSError as e:
                    logger.warning(f"Failed to delete adapter {v.adapter_path}: {e}")

        conv_result = await self.db.execute(
            select(Conversation).where(Conversation.user_id == user.id)
        )
        conversations = conv_result.scalars().all()
        deleted["conversations"] = len(conversations)

        msg_count_result = await self.db.execute(
            select(Message).join(Conversation).where(Conversation.user_id == user.id)
        )
        deleted["messages"] = len(msg_count_result.scalars().all())

        unlearn_result = await self.db.execute(
            select(UnlearningRequest).where(UnlearningRequest.user_id == user.id)
        )
        deleted["unlearning_requests"] = len(unlearn_result.scalars().all())

        audit_result = await self.db.execute(
            select(AuditLedger).where(AuditLedger.user_id == user.id)
        )
        deleted["audit_entries"] = len(audit_result.scalars().all())

        await self.db.delete(user)
        await self.db.flush()
        deleted["user"] = True

        logger.info(f"User account deleted: id={user.id}, data={deleted}")
        return deleted
