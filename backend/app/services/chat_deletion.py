"""Chat deletion service — surgical unlearning over Assistant conversations.

Deleting a chat from the Surgical Unlearning page is itself a *deletion
operation* and therefore mints a signed certificate exactly like a dataset
deletion. Two modes are supported:

- ``full``      — the entire chat session row is removed. The "after" state is
                  empty content, so the post root is the empty-tree root.
- ``sensitive`` — only the detected sensitive data is scrubbed from the
                  transcript; the remaining conversation stays readable.

In both cases the service computes pre/post Merkle roots over the transcript
lines, records the hashes of every removed segment in the certificate, signs
it, persists the PDF and logs an audit event.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationFailedError
from app.services.certificate import CertificateService
from app.services.crypto import MerkleTree, sha256_hex
from app.services.pii_detection import PIIDetectionEngine, redact_sensitive

logger = logging.getLogger("veriunlearn.chat_deletion")

_EMPTY_ROOT = MerkleTree([]).root  # sha256_hex("empty-tree")


class ChatDeletionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.certificates = CertificateService(session)
        self._pii = PIIDetectionEngine()

    async def delete(
        self,
        *,
        user_id: str,
        chat_session_id: str,
        mode: str,
        actor: str | None = None,
    ) -> dict[str, Any]:
        if mode not in {"full", "sensitive"}:
            raise ValidationFailedError("mode must be 'full' or 'sensitive'")

        from app.db.models import ChatSession

        chat = await self.session.get(ChatSession, chat_session_id)
        if chat is None:
            raise NotFoundError(f"Chat session {chat_session_id} not found")
        if chat.user_id != user_id:
            raise ValidationFailedError("You can only delete your own chat sessions")

        lines = chat.content.split("\n") if chat.content else []
        line_hashes = [sha256_hex(line) for line in lines]
        pre_root = MerkleTree(line_hashes).root
        content_before = "\n".join(lines)[:2000]

        categories = self._categories(chat.sensitive_data)

        if mode == "full":
            after_content = ""
            removed_hashes = line_hashes
            post_root = _EMPTY_ROOT
            method = "chat_delete"
            await self.session.delete(chat)
        else:
            after_content = redact_sensitive(chat.content)
            after_lines = after_content.split("\n") if after_content else []
            after_hashes = {sha256_hex(line) for line in after_lines}
            removed_hashes = sorted({h for h in line_hashes if h not in after_hashes})
            post_root = MerkleTree([sha256_hex(line) for line in after_lines]).root
            method = "sensitive_redaction"
            chat.content = after_content
            chat.sensitive_data = ""
            await self.session.flush()

        cert = await self.certificates.issue(
            subject_user_id=user_id,
            deletion_type="chat",
            deleted_record_count=max(1, len(removed_hashes)),
            dataset_id=None,
            model_id=None,
            model_version=0,
            shard_ids=[],
            pre_merkle_root=pre_root,
            post_merkle_root=post_root,
            deleted_record_hashes=sorted(removed_hashes),
            method=method,
            certified_bound=None,
            actor=actor or user_id,
        )
        cert.certificate_json = {
            **cert.certificate_json,
            "chat_session_id": chat_session_id,
            "mode": mode,
            "sensitive_categories": categories,
            "content_before": content_before,
            "content_after": after_content[:2000],
        }
        await self.certificates.persist_pdf(cert)
        await self.session.flush()

        from app.services.audit import AuditService

        await AuditService(self.session).log(
            event_type="chat.deleted",
            actor=actor or user_id,
            subject=chat_session_id,
            certificate_id=cert.id,
            payload={
                "mode": mode,
                "chat_session_id": chat_session_id,
                "sensitive_categories": categories,
                "removed_segments": len(removed_hashes),
            },
        )
        await self.session.commit()

        logger.info("Chat %s deleted (mode=%s) → certificate %s", chat_session_id, mode, cert.id)
        return {
            "chat_session_id": chat_session_id,
            "mode": mode,
            "certificate_id": cert.id,
            "deletion_type": cert.deletion_type,
            "method": cert.method,
            "deleted_record_count": cert.deleted_record_count,
            "pre_merkle_root": cert.pre_merkle_root,
            "post_merkle_root": cert.post_merkle_root,
            "sensitive_categories": categories,
            "verification_status": cert.verification_status,
            "timestamp": cert.timestamp,
        }

    def _categories(self, sensitive_data: str) -> list[str]:
        if not sensitive_data:
            return []
        return [s.strip() for s in sensitive_data.split(",") if s.strip()]