import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

from app.infrastructure.database.models import Base, UnlearningRequestModel, UnlearningJobModel, WebhookModel
from app.workers.session import _sync_engine, _SyncSessionLocal
from app.workers.unlearning_tasks import execute_unlearning, generate_deletion_proof, cleanup_deletion_queue


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(_sync_engine)
    yield
    Base.metadata.drop_all(_sync_engine)


@pytest.fixture
def sync_session(setup_db):
    session = _SyncSessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()


class TestUnlearningTasks:
    def test_execute_unlearning_not_found(self):
        result = execute_unlearning("nonexistent-id")
        assert result["status"] == "not_found"

    def test_generate_deletion_proof_not_found(self):
        result = generate_deletion_proof("nonexistent-job")
        assert result["status"] == "not_found"

    def test_cleanup_deletion_queue(self):
        result = cleanup_deletion_queue()
        assert result["status"] == "completed"

    def test_execute_unlearning_success(self, sync_session):
        req = UnlearningRequestModel(
            id="test-unlearn-req-1",
            tenant_id="tenant-1",
            requested_by="user-1",
            target_type="user",
            target_id="data_user_001",
            reason="GDPR right to be forgotten",
            gdpr_article="17",
            status="pending",
            priority="high",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        sync_session.add(req)
        sync_session.commit()

        mock_client = MagicMock()
        mock_client.execute_unlearning = AsyncMock(return_value={
            "success": True,
            "algorithm": "SISA",
            "processing_time_ms": 500,
        })

        with (
            patch("app.workers.unlearning_tasks.worker_session") as mock_ws,
            patch("app.workers.unlearning_tasks.ml_engine_client", mock_client),
        ):
            mock_ws.return_value.__enter__.return_value = sync_session
            result = execute_unlearning("test-unlearn-req-1")
            assert result["status"] == "completed"
            assert result["algorithm"] == "SISA"

    def test_generate_deletion_proof_success(self, sync_session):
        req = UnlearningRequestModel(
            id="test-unlearn-req-2",
            tenant_id="tenant-1",
            requested_by="user-1",
            target_type="user",
            target_id="data_user_002",
            reason="GDPR right to be forgotten",
            status="completed",
            priority="high",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        sync_session.add(req)
        sync_session.commit()

        job = UnlearningJobModel(
            id="test-job-1",
            request_id="test-unlearn-req-2",
            algorithm="hybrid",
            model_id="data_user_002",
            status="completed",
            progress=100.0,
            created_at=datetime.now(timezone.utc),
        )
        sync_session.add(job)
        sync_session.commit()

        mock_client = MagicMock()
        mock_client.generate_proof = AsyncMock(return_value={
            "merkle_root": "abcdef1234567890",
            "leaf_count": 1,
            "signature_hex": "sig_hex_value",
            "algorithm": "ed25519",
        })

        with (
            patch("app.workers.unlearning_tasks.worker_session") as mock_ws,
            patch("app.workers.unlearning_tasks.ml_engine_client", mock_client),
        ):
            mock_ws.return_value.__enter__.return_value = sync_session
            result = generate_deletion_proof("test-job-1")
            assert result["status"] == "completed"
            assert result["merkle_root"] == "abcdef1234567890"


class TestNotificationTasks:
    def test_dispatch_webhook_skips_inactive(self, sync_session):
        from app.workers.notification_tasks import dispatch_webhook

        wh = WebhookModel(
            id="test-wh-inactive",
            tenant_id="tenant-1",
            name="Inactive",
            url="https://example.com",
            secret="s3cret!",
            events=["test.event"],
            is_active=0,
            status="disabled",
            headers={},
            retry_count=3,
            timeout_ms=5000,
            consecutive_failures=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        sync_session.add(wh)
        sync_session.commit()

        result = dispatch_webhook("test-wh-inactive", "test.event", {"key": "value"})
        assert result["status"] == "skipped"

    def test_retry_failed_webhooks(self, sync_session):
        from app.workers.notification_tasks import retry_failed_webhooks

        wh = WebhookModel(
            id="test-wh-retry",
            tenant_id="tenant-1",
            name="Retry Me",
            url="https://example.com/retry",
            secret="s3cret!",
            events=["test.event"],
            is_active=1,
            status="active",
            headers={},
            retry_count=3,
            timeout_ms=5000,
            consecutive_failures=2,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        sync_session.add(wh)
        sync_session.commit()

        with patch("app.workers.notification_tasks.dispatch_webhook.delay") as mock_delay:
            mock_delay.return_value = None
            result = retry_failed_webhooks()
            assert result["status"] == "completed"
            assert mock_delay.call_count >= 1
