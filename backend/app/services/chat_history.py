"""Chat history audit service — persists Assistant conversations with the
sensitive-data categories detected inside them."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from app.db.session import session_factory
from app.repositories.chat_repo import ChatSessionRepository
from app.services.pii_detection import PIIDetectionEngine

_MAX_NAME = 100
_MAX_CONTENT = 5000
_SENSITIVE_LABELS = {
    "email": "email",
    "phone": "phone",
    "address": "address",
    "financial": "credit card / financial",
    "government_id": "government ID",
    "dob": "date of birth",
    "medical": "medical",
    "credentials": "password / credentials",
    "identifier": "customer/employee ID",
    "pii": "personal name",
    "biometric": "biometric",
    "employment": "employment",
    "education": "education",
    "legal": "legal",
    "business_confidential": "business confidential",
    "government_military": "government / military",
    "intellectual_property": "intellectual property",
    "security_info": "security information",
    "personal_comms": "personal communication",
    "location": "location data",
    "children": "children's data",
    "media": "images / media",
    "source_code_secret": "source code secret",
    "customer_client": "customer / client data",
    "research": "research data",
    "corporate_creds": "corporate credentials",
    "sensitive_attribute": "sensitive attribute",
    "recovery": "recovery information",
    "payment_docs": "payment documents",
    "device": "device information",
    "access_logs": "access logs",
    "meeting": "meeting data",
    "regulatory": "regulated data",
}


class ChatHistoryService:
    def __init__(self) -> None:
        self._pii = PIIDetectionEngine()

    async def persist(self, *, user_id: str, session_id: str | None, messages: list[dict], assistant_text: str) -> dict:
        """Create or append a chat session and return its record."""
        transcript_lines = [f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages]
        transcript_lines.append(f"assistant: {assistant_text}")
        transcript = "\n".join(transcript_lines)
        transcript = transcript[-_MAX_CONTENT:] if len(transcript) > _MAX_CONTENT else transcript

        structured: list[dict] = [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in messages]
        structured.append({"role": "assistant", "content": assistant_text})
        messages_json = json.dumps(structured)

        findings = self._pii.analyze(transcript)
        categories: list[str] = []
        seen: set[str] = set()
        for f in findings.findings:
            label = _SENSITIVE_LABELS.get(f.category, f.category)
            if label not in seen:
                seen.add(label)
                categories.append(label)
        sensitive = ", ".join(categories)
        message_count = len(messages) + (1 if assistant_text else 0)

        name = next(
            (m.get("content", "")[: _MAX_NAME] for m in messages if m.get("role") == "user" and m.get("content")),
            "Untitled chat",
        )

        async with session_factory() as session:
            repo = ChatSessionRepository(session)
            chat = None
            if session_id:
                chat = await repo.get_by_id(session_id)
                if chat is not None and chat.user_id != user_id:
                    chat = None  # never touch another user's session
            if chat is None:
                chat = await repo.create(user_id=user_id, name=name)
                session_id = chat.id
            chat = await repo.append(
                chat,
                transcript=transcript,
                messages_json=messages_json,
                sensitive_data=sensitive,
                message_count=message_count,
            )
            await session.commit()

        return {
            "session_id": chat.id,
            "name": chat.name,
            "content": chat.content,
            "messages": json.loads(chat.messages_json or "[]"),
            "sensitive_data": chat.sensitive_data,
            "message_count": chat.message_count,
            "updated_at": _iso(chat.updated_at),
        }

    async def list_sessions(
        self,
        user_id: str,
        limit: int = 200,
        *,
        search: str | None = None,
        from_ts: datetime | None = None,
        to_ts: datetime | None = None,
    ) -> list[dict]:
        async with session_factory() as session:
            repo = ChatSessionRepository(session)
            rows = await repo.list_for_user(
                user_id,
                limit=limit,
                search=search,
                from_ts=from_ts,
                to_ts=to_ts,
            )
            return [
                {
                    "session_id": c.id,
                    "name": c.name,
                    "content": c.content,
                    "messages": json.loads(c.messages_json or "[]"),
                    "sensitive_data": c.sensitive_data,
                    "message_count": c.message_count,
                    "created_at": _iso(c.created_at),
                    "updated_at": _iso(c.updated_at),
                }
                for c in rows
            ]

    async def get_session(self, user_id: str, session_id: str) -> dict | None:
        async with session_factory() as session:
            repo = ChatSessionRepository(session)
            chat = await repo.get_by_id(session_id)
            if chat is None or chat.user_id != user_id:
                return None
            return {
                "session_id": chat.id,
                "name": chat.name,
                "content": chat.content,
                "messages": json.loads(chat.messages_json or "[]"),
                "sensitive_data": chat.sensitive_data,
                "message_count": chat.message_count,
                "created_at": _iso(chat.created_at),
                "updated_at": _iso(chat.updated_at),
            }


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()