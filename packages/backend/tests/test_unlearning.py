import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


TEST_EMAIL = "unlearning-test@example.com"
TEST_PASSWORD = "SecureP@ss123!"


async def _register_and_login(client: AsyncClient, email: str = TEST_EMAIL) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": TEST_PASSWORD, "full_name": "Unlearning Test"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": TEST_PASSWORD},
    )
    return resp.json()["access_token"]


@pytest.fixture
def mock_ml_engine():
    with patch("app.domain.unlearning.services.ml_engine_client") as mock:
        mock.execute_unlearning = AsyncMock(return_value={
            "status": "completed",
            "deletion_steps": [
                {"resource_type": "postgres", "resource_id": "msg-123", "operation": "delete"},
                {"resource_type": "qdrant", "resource_id": "vec-456", "operation": "delete"},
            ],
            "processing_time_ms": 1500,
        })
        yield mock


class TestUnlearningServiceDirect:
    async def test_create_request_and_job(self, client: AsyncClient, mock_ml_engine):
        from app.core.database import db
        from app.domain.unlearning.services import UnlearningService
        from app.domain.unlearning.entities import TargetType, UnlearningPriority, UnlearningAlgorithm
        from app.domain.audit.services import AuditService
        from app.infrastructure.database.repositories.unlearning import (
            SQLAlchemyUnlearningRequestRepository,
            SQLAlchemyUnlearningJobRepository,
            SQLAlchemyDeletionQueueRepository,
            SQLAlchemyModelVersionRepository,
        )
        from app.infrastructure.database.repositories.audit import SQLAlchemyAuditEventRepository

        async with db.session_factory() as session:
            audit_repo = SQLAlchemyAuditEventRepository(session)
            audit_svc = AuditService(repo=audit_repo)
            svc = UnlearningService(
                request_repo=SQLAlchemyUnlearningRequestRepository(session),
                job_repo=SQLAlchemyUnlearningJobRepository(session),
                deletion_queue_repo=SQLAlchemyDeletionQueueRepository(session),
                model_version_repo=SQLAlchemyModelVersionRepository(session),
                audit_service=audit_svc,
            )

            request, job = await svc.create_request(
                tenant_id="test-tenant",
                requested_by="test-user",
                target_type=TargetType.MESSAGE,
                target_id="msg-123",
                reason="GDPR right to erasure",
                priority=UnlearningPriority.HIGH,
            )

            assert request.id is not None
            assert request.status.value == "completed"
            assert request.target_type == TargetType.MESSAGE
            assert request.target_id == "msg-123"

            assert job is not None
            assert job.status.value == "completed"
            assert job.progress == 1.0

            requests, total = await svc.list_requests("test-tenant", page=1, page_size=25)
            assert total >= 1
            assert any(r.id == request.id for r in requests)

    async def test_get_request_not_found(self, client: AsyncClient):
        from app.core.database import db
        from app.domain.unlearning.services import UnlearningService
        from app.core.exceptions import NotFoundError
        from app.domain.audit.services import AuditService
        from app.infrastructure.database.repositories.unlearning import (
            SQLAlchemyUnlearningRequestRepository,
            SQLAlchemyUnlearningJobRepository,
            SQLAlchemyDeletionQueueRepository,
            SQLAlchemyModelVersionRepository,
        )
        from app.infrastructure.database.repositories.audit import SQLAlchemyAuditEventRepository

        async with db.session_factory() as session:
            audit_repo = SQLAlchemyAuditEventRepository(session)
            audit_svc = AuditService(repo=audit_repo)
            svc = UnlearningService(
                request_repo=SQLAlchemyUnlearningRequestRepository(session),
                job_repo=SQLAlchemyUnlearningJobRepository(session),
                deletion_queue_repo=SQLAlchemyDeletionQueueRepository(session),
                model_version_repo=SQLAlchemyModelVersionRepository(session),
                audit_service=audit_svc,
            )

            with pytest.raises(NotFoundError):
                await svc.get_request("test-tenant", "non-existent-id")

    async def test_create_model_version(self, client: AsyncClient):
        from app.core.database import db
        from app.domain.unlearning.services import UnlearningService
        from app.domain.audit.services import AuditService
        from app.infrastructure.database.repositories.unlearning import (
            SQLAlchemyUnlearningRequestRepository,
            SQLAlchemyUnlearningJobRepository,
            SQLAlchemyDeletionQueueRepository,
            SQLAlchemyModelVersionRepository,
        )
        from app.infrastructure.database.repositories.audit import SQLAlchemyAuditEventRepository

        async with db.session_factory() as session:
            audit_repo = SQLAlchemyAuditEventRepository(session)
            audit_svc = AuditService(repo=audit_repo)
            svc = UnlearningService(
                request_repo=SQLAlchemyUnlearningRequestRepository(session),
                job_repo=SQLAlchemyUnlearningJobRepository(session),
                deletion_queue_repo=SQLAlchemyDeletionQueueRepository(session),
                model_version_repo=SQLAlchemyModelVersionRepository(session),
                audit_service=audit_svc,
            )

            v1 = await svc.create_model_version(
                tenant_id="test-tenant",
                name="test-model",
                algorithm="hybrid",
                config={"batch_size": 32},
                shard_count=2,
            )
            assert v1.version == 1
            assert v1.name == "test-model"
            assert v1.shard_count == 2

            v2 = await svc.create_model_version(
                tenant_id="test-tenant",
                name="test-model",
                algorithm="hybrid",
            )
            assert v2.version == 2
            assert v2.parent_version_id == v1.id


class TestUnlearningAPI:
    @pytest.mark.usefixtures("mock_ml_engine")
    async def test_create_unlearning_request(self, client: AsyncClient):
        token = await _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/v1/unlearning/requests",
            params={
                "target_type": "message",
                "target_id": "api-test-msg-1",
                "reason": "API test deletion",
                "priority": "high",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["request_id"] is not None
        assert data["status"] in ("completed", "queued")

    async def test_list_unlearning_requests(self, client: AsyncClient):
        token = await _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/unlearning/requests", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "meta" in data

    async def test_get_unlearning_request_not_found(self, client: AsyncClient):
        token = await _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/unlearning/requests/non-existent-id", headers=headers)
        assert resp.status_code == 404

    async def test_get_queue_status(self, client: AsyncClient):
        token = await _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/unlearning/queue", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "queue" in data
        assert "pending" in data["queue"]
        assert "processing" in data["queue"]

    async def test_create_unlearning_request_unauthorized(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/unlearning/requests",
            params={"target_type": "message", "target_id": "test"},
        )
        assert resp.status_code == 401

    async def test_list_requests_requires_permission(self, client: AsyncClient):
        from app.core.database import db
        from sqlalchemy import update
        from app.infrastructure.database.models import UserModel

        token = await _register_and_login(client, "viewer-unl@example.com")
        async with db.session_factory() as session:
            await session.execute(
                update(UserModel).where(UserModel.email == "viewer-unl@example.com").values(role="viewer")
            )
            await session.commit()

        token = (await client.post("/api/v1/auth/login", json={"email": "viewer-unl@example.com", "password": TEST_PASSWORD})).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/unlearning/requests", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["meta"]["total"] >= 0


class TestVerificationAPI:
    async def test_list_proofs_empty(self, client: AsyncClient):
        token = await _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/verify/proofs", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert data["meta"]["total"] == 0

    async def test_get_proof_not_found(self, client: AsyncClient):
        token = await _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/verify/proofs/non-existent", headers=headers)
        assert resp.status_code == 404

    async def test_verify_proof_not_found(self, client: AsyncClient):
        from app.core.database import db
        from sqlalchemy import update
        from app.infrastructure.database.models import UserModel

        token = await _register_and_login(client, "verify-admin@example.com")
        async with db.session_factory() as session:
            await session.execute(
                update(UserModel).where(UserModel.email == "verify-admin@example.com").values(role="admin")
            )
            await session.commit()
        token = (await client.post("/api/v1/auth/login", json={"email": "verify-admin@example.com", "password": TEST_PASSWORD})).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post("/api/v1/verify/proofs/non-existent/verify", headers=headers)
        assert resp.status_code == 404

    async def test_get_certificate(self, client: AsyncClient):
        token = await _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/verify/certificates/test-hash", headers=headers)
        assert resp.status_code in (200, 404)


class TestVerificationServiceDirect:
    async def test_generate_and_verify_proof(self, client: AsyncClient):
        from app.core.database import db
        from app.domain.verification.services import VerificationService
        from app.domain.audit.services import AuditService
        from app.infrastructure.database.repositories.verification import (
            SQLAlchemyDeletionProofRepository,
            SQLAlchemyProofVerificationRepository,
        )
        from app.infrastructure.database.repositories.audit import SQLAlchemyAuditEventRepository
        from unittest.mock import patch, AsyncMock

        async with db.session_factory() as session:
            audit_repo = SQLAlchemyAuditEventRepository(session)
            audit_svc = AuditService(repo=audit_repo)
            svc = VerificationService(
                proof_repo=SQLAlchemyDeletionProofRepository(session),
                verification_repo=SQLAlchemyProofVerificationRepository(session),
                audit_service=audit_svc,
            )

            with patch("app.domain.verification.services.ml_engine_client") as mock:
                mock.generate_proof = AsyncMock(return_value={
                    "merkle_root": "abc123",
                    "tree_depth": 3,
                    "merkle_tree": {"levels": [], "leaves": []},
                    "signature_hex": "sig123",
                    "public_key_pem": "pubkey123",
                    "leaf_count": 2,
                })
                mock.verify_proof = AsyncMock(return_value={
                    "is_valid": True,
                    "algorithm": "ed25519",
                })

                proof = await svc.generate_proof(
                    tenant_id="test-tenant",
                    job_id="job-1",
                    request_id="req-1",
                    deletion_steps=["step1", "step2"],
                )
                assert proof.id is not None
                assert proof.merkle_root == "abc123"
                assert not proof.verified

                verification = await svc.verify_proof(
                    proof_id=proof.id,
                    verifier_id="test-user",
                )
                assert verification.is_valid
                assert verification.proof_id == proof.id

                retrieved = await svc.get_proof(proof.id)
                assert retrieved.verified

    async def test_list_proofs(self, client: AsyncClient):
        from app.core.database import db
        from app.domain.verification.services import VerificationService
        from app.domain.audit.services import AuditService
        from app.infrastructure.database.repositories.verification import (
            SQLAlchemyDeletionProofRepository,
            SQLAlchemyProofVerificationRepository,
        )
        from app.infrastructure.database.repositories.audit import SQLAlchemyAuditEventRepository
        from unittest.mock import patch, AsyncMock

        async with db.session_factory() as session:
            audit_repo = SQLAlchemyAuditEventRepository(session)
            audit_svc = AuditService(repo=audit_repo)
            svc = VerificationService(
                proof_repo=SQLAlchemyDeletionProofRepository(session),
                verification_repo=SQLAlchemyProofVerificationRepository(session),
                audit_service=audit_svc,
            )

            with patch("app.domain.verification.services.ml_engine_client") as mock:
                mock.generate_proof = AsyncMock(return_value={
                    "merkle_root": "root1",
                    "tree_depth": 2,
                    "merkle_tree": {},
                    "signature_hex": "sig1",
                    "public_key_pem": "pk1",
                    "leaf_count": 1,
                })

                await svc.generate_proof(
                    tenant_id="list-test",
                    job_id="job-list",
                    request_id="req-list",
                    deletion_steps=["step"],
                )

            results, total = await svc.list_proofs("list-test", page=1, page_size=10)
            assert total >= 1
            assert any(p.merkle_root == "root1" for p in results)
