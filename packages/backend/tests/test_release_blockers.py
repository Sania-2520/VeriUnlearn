"""Tests for the v1.0 release-blocker fixes.

Covers:
* ``MLEngineClientError`` transient/permanent classification (used by Celery
  retry logic).
* Missing email templates (``deletion_confirmed``, ``account_deleted``).
* RAG upload persistence + Celery dispatch for binary documents.
* ``VerificationService.get_certificate`` real lookup by certificate hash.
"""

import os
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# MLEngineClientError classification
# ---------------------------------------------------------------------------


class TestMLEngineClientError:
    def test_transient_5xx(self):
        from app.infrastructure.external.ml_engine import MLEngineClientError

        err = MLEngineClientError("boom", status_code=503)
        assert err.is_transient is True

    def test_transient_429(self):
        from app.infrastructure.external.ml_engine import MLEngineClientError

        err = MLEngineClientError("rate limited", status_code=429)
        assert err.is_transient is True

    def test_transient_connection_error(self):
        from app.infrastructure.external.ml_engine import MLEngineClientError

        err = MLEngineClientError("connection refused", status_code=None)
        assert err.is_transient is True

    def test_permanent_4xx(self):
        from app.infrastructure.external.ml_engine import MLEngineClientError

        err = MLEngineClientError("not found", status_code=404)
        assert err.is_transient is False

    def test_backward_compatible_default_status(self):
        from app.infrastructure.external.ml_engine import MLEngineClientError

        err = MLEngineClientError("legacy message")
        assert err.status_code is None
        assert str(err) == "legacy message"


# ---------------------------------------------------------------------------
# Email templates
# ---------------------------------------------------------------------------


class TestEmailTemplates:
    def test_deletion_confirmed_template(self):
        from app.infrastructure.external.email_service import EmailService

        body = EmailService._render_template(
            "deletion_confirmed", name="Ada", proof_id="proof-123"
        )
        assert "Deletion Confirmed" in body
        assert "Ada" in body
        assert "proof-123" in body

    def test_account_deleted_template(self):
        from app.infrastructure.external.email_service import EmailService

        body = EmailService._render_template("account_deleted", name="Ada")
        assert "Account Deleted" in body
        assert "Ada" in body

    def test_unknown_template_falls_back(self):
        from app.infrastructure.external.email_service import EmailService

        body = EmailService._render_template("nope")
        assert "No template found" in body


# ---------------------------------------------------------------------------
# RAG upload persistence + Celery dispatch
# ---------------------------------------------------------------------------


class TestRAGUpload:
    @pytest.fixture(autouse=True)
    def _patch_storage(self, tmp_path):
        # The upload endpoint reads ``app.core.config.settings`` directly, so
        # redirect its storage dir to a temp location for the test.
        from app.core.config import settings

        original = settings.rag_storage_dir
        settings.rag_storage_dir = str(tmp_path)
        yield
        settings.rag_storage_dir = original

    async def _register(self, client: AsyncClient) -> str:
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "rag-upload@example.com",
                "password": "SecureP@ss123!",
                "full_name": "RAG Upload",
            },
        )
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "rag-upload@example.com", "password": "SecureP@ss123!"},
        )
        return resp.json()["access_token"]

    @pytest.mark.usefixtures("_patch_storage")
    async def test_text_upload_ingested_inline(self, client: AsyncClient, tmp_path):
        from app.core.database import db
        from app.infrastructure.database.models import RagDocumentModel
        from sqlalchemy import select

        token = await self._register(client)
        headers = {"Authorization": f"Bearer {token}"}

        files = {
            "file": ("notes.txt", b"hello world from the test document", "text/plain")
        }
        with patch(
            "app.api.v1.rag.ml_engine_client.ingest_document",
            AsyncMock(
                return_value={
                    "document_id": "doc-1",
                    "status": "indexed",
                    "chunk_count": 2,
                }
            ),
        ):
            resp = await client.post(
                "/api/v1/rag/documents/upload", files=files, headers=headers
            )
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "indexed"

        async with db.session_factory() as session:
            result = await session.execute(
                select(RagDocumentModel).where(RagDocumentModel.id == data["document_id"])
            )
            doc = result.scalar_one_or_none()
            assert doc is not None
            # The upload must be persisted to disk with a real storage_path.
            assert doc.storage_path != ""
            assert os.path.exists(doc.storage_path)
            assert doc.content_hash is not None

    @pytest.mark.usefixtures("_patch_storage")
    async def test_pdf_upload_dispatches_process_document(
        self, client: AsyncClient, tmp_path
    ):
        token = await self._register(client)
        headers = {"Authorization": f"Bearer {token}"}

        files = {
            "file": (
                "scan.pdf",
                b"%PDF-1.4 fake binary payload \x00\x01\x02",
                "application/pdf",
            )
        }
        with (
            patch("app.api.v1.rag.ml_engine_client.ingest_document", AsyncMock()) as mock_ingest,
            patch("app.workers.rag_tasks.process_document.delay") as mock_delay,
        ):
            resp = await client.post(
                "/api/v1/rag/documents/upload", files=files, headers=headers
            )
            mock_ingest.assert_not_awaited()
            mock_delay.assert_called_once_with(resp.json()["document_id"])
        assert resp.status_code == 202
        assert resp.json()["status"] == "processing"

    @pytest.mark.usefixtures("_patch_storage")
    async def test_image_upload_dispatches_ocr(self, client: AsyncClient, tmp_path):
        token = await self._register(client)
        headers = {"Authorization": f"Bearer {token}"}

        files = {
            "file": (
                "scan.png",
                b"\x89PNG\r\n\x1a\nfake image bytes",
                "image/png",
            )
        }
        with (
            patch("app.api.v1.rag.ml_engine_client.ingest_document", AsyncMock()) as mock_ingest,
            patch("app.workers.rag_tasks.ocr_process.delay") as mock_delay,
        ):
            resp = await client.post(
                "/api/v1/rag/documents/upload", files=files, headers=headers
            )
            mock_ingest.assert_not_awaited()
            mock_delay.assert_called_once_with(resp.json()["document_id"])
        assert resp.status_code == 202
        assert resp.json()["status"] == "processing"

    @pytest.mark.usefixtures("_patch_storage")
    async def test_text_upload_falls_back_to_celery_on_ml_failure(
        self, client: AsyncClient, tmp_path
    ):
        from app.infrastructure.external.ml_engine import MLEngineClientError

        token = await self._register(client)
        headers = {"Authorization": f"Bearer {token}"}

        files = {
            "file": ("notes.md", b"# markdown notes", "text/markdown")
        }
        with (
            patch(
                "app.api.v1.rag.ml_engine_client.ingest_document",
                AsyncMock(side_effect=MLEngineClientError("engine down", 503)),
            ),
            patch("app.workers.rag_tasks.process_document.delay") as mock_delay,
        ):
            resp = await client.post(
                "/api/v1/rag/documents/upload", files=files, headers=headers
            )
            mock_delay.assert_called_once_with(resp.json()["document_id"])
        assert resp.status_code == 202
        assert resp.json()["status"] == "processing"


# ---------------------------------------------------------------------------
# VerificationService.get_certificate
# ---------------------------------------------------------------------------


class TestVerificationCertificateLookup:
    async def test_get_certificate_returns_stored(self, client: AsyncClient):
        from app.core.database import db
        from app.domain.audit.services import AuditService
        from app.domain.verification.services import VerificationService
        from app.infrastructure.database.repositories.audit import (
            SQLAlchemyAuditEventRepository,
        )
        from app.infrastructure.database.repositories.verification import (
            SQLAlchemyDeletionProofRepository,
            SQLAlchemyProofVerificationRepository,
        )

        async with db.session_factory() as session:
            audit_repo = SQLAlchemyAuditEventRepository(session)
            audit_svc = AuditService(repo=audit_repo)
            svc = VerificationService(
                proof_repo=SQLAlchemyDeletionProofRepository(session),
                verification_repo=SQLAlchemyProofVerificationRepository(session),
                audit_service=audit_svc,
            )

            # Create a proof carrying a certificate, then look it up by hash.
            with patch("app.domain.verification.services.ml_engine_client") as mock:
                mock.generate_proof = AsyncMock(return_value={
                    "merkle_root": "root-cert",
                    "tree_depth": 2,
                    "merkle_tree": {},
                    "signature_hex": "sig",
                    "public_key_pem": "pk",
                    "leaf_count": 1,
                })
                proof = await svc.generate_proof(
                    tenant_id="cert-tenant",
                    job_id="job-cert",
                    request_id="req-cert",
                    deletion_steps=["step"],
                )
            proof.certificate = "certificate-bytes"
            proof.certificate_hash = "hash-123"
            await svc._proof_repo.update(proof)

            found = await svc.get_certificate("hash-123")
            assert found is not None
            assert found["certificate"] == "certificate-bytes"
            assert found["proof_id"] == proof.id

    async def test_get_certificate_missing_returns_none(self, client: AsyncClient):
        from app.core.database import db
        from app.domain.audit.services import AuditService
        from app.domain.verification.services import VerificationService
        from app.infrastructure.database.repositories.audit import (
            SQLAlchemyAuditEventRepository,
        )
        from app.infrastructure.database.repositories.verification import (
            SQLAlchemyDeletionProofRepository,
            SQLAlchemyProofVerificationRepository,
        )

        async with db.session_factory() as session:
            audit_repo = SQLAlchemyAuditEventRepository(session)
            audit_svc = AuditService(repo=audit_repo)
            svc = VerificationService(
                proof_repo=SQLAlchemyDeletionProofRepository(session),
                verification_repo=SQLAlchemyProofVerificationRepository(session),
                audit_service=audit_svc,
            )
            assert await svc.get_certificate("no-such-hash") is None
