from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from app.infrastructure.external.ml_engine import MLEngineClientError
from httpx import AsyncClient

TEST_PASSWORD = "SecureP@ss123!"


async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": TEST_PASSWORD, "full_name": "Endpoint Test"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": TEST_PASSWORD},
    )
    return resp.json()["access_token"]


async def _register_and_login_as_admin(client: AsyncClient, email: str) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": TEST_PASSWORD, "full_name": "Admin Test"},
    )
    from app.core.database import db
    from app.infrastructure.database.models import UserModel
    from sqlalchemy import update

    async with db.session_factory() as session:
        await session.execute(
            update(UserModel).where(UserModel.email == email).values(role="admin")
        )
        await session.commit()
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": TEST_PASSWORD},
    )
    return resp.json()["access_token"]


async def _login(client: AsyncClient, email: str) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": TEST_PASSWORD},
    )
    return resp.json()["access_token"]


async def _set_user_role(client: AsyncClient, email: str, role: str):
    from app.core.database import db
    from app.infrastructure.database.models import UserModel
    from sqlalchemy import update

    async with db.session_factory() as session:
        await session.execute(
            update(UserModel).where(UserModel.email == email).values(role=role)
        )
        await session.commit()


def _make_mock_response(data, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = data
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=resp,
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


def _patch_training_httpx(response_data, status_code=200):
    mock_resp = _make_mock_response(response_data, status_code)
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False
    return patch("app.api.v1.training.httpx.AsyncClient", return_value=mock_client)


def _patch_models_httpx(response_data, status_code=200):
    mock_resp = _make_mock_response(response_data, status_code)
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False
    return patch("app.api.v1.models.httpx.AsyncClient", return_value=mock_client)


# ---------------------------------------------------------------------------
# Training Endpoints (/api/v1/training/...)
# Training router requires TRAINING_WRITE (admin only)
# ---------------------------------------------------------------------------

class TestTrainingJobs:
    async def test_list_jobs_success(self, client: AsyncClient):
        token = await _register_and_login_as_admin(client, "tr-list@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        mock_data = {"jobs": [{"id": "j1", "status": "completed"}], "total": 1}
        with _patch_training_httpx(mock_data):
            resp = await client.get("/api/v1/training/jobs", headers=headers)

        assert resp.status_code == 200
        assert resp.json() == mock_data

    async def test_list_jobs_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/v1/training/jobs")
        assert resp.status_code == 401

    async def test_list_jobs_forbidden_member(self, client: AsyncClient):
        token = await _register_and_login(client, "tr-list-mem@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/training/jobs", headers=headers)
        assert resp.status_code == 403

    async def test_list_jobs_ml_engine_error(self, client: AsyncClient):
        token = await _register_and_login_as_admin(client, "tr-list-err@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        with _patch_training_httpx({}, status_code=500):
            resp = await client.get("/api/v1/training/jobs", headers=headers)

        assert resp.status_code == 502

    async def test_get_job_success(self, client: AsyncClient):
        token = await _register_and_login_as_admin(client, "tr-get@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        mock_data = {"job_id": "job-abc", "status": "running", "progress": 0.5}
        with _patch_training_httpx(mock_data):
            resp = await client.get("/api/v1/training/jobs/job-abc", headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == "job-abc"
        assert data["status"] == "running"

    async def test_get_job_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/v1/training/jobs/job-abc")
        assert resp.status_code == 401

    async def test_get_job_forbidden_member(self, client: AsyncClient):
        token = await _register_and_login(client, "tr-get-mem@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/training/jobs/job-abc", headers=headers)
        assert resp.status_code == 403


class TestTrainingGPU:
    async def test_gpu_status_success(self, client: AsyncClient):
        token = await _register_and_login_as_admin(client, "tr-gpu@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        mock_data = {"gpus": [{"id": 0, "name": "A100", "utilization": 82.5}]}
        with _patch_training_httpx(mock_data):
            resp = await client.get("/api/v1/training/gpu", headers=headers)

        assert resp.status_code == 200
        assert "gpus" in resp.json()
        assert resp.json()["gpus"][0]["name"] == "A100"

    async def test_gpu_status_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/v1/training/gpu")
        assert resp.status_code == 401

    async def test_gpu_status_forbidden_member(self, client: AsyncClient):
        token = await _register_and_login(client, "tr-gpu-mem@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/training/gpu", headers=headers)
        assert resp.status_code == 403


class TestTrainingQueue:
    async def test_queue_stats_success(self, client: AsyncClient):
        token = await _register_and_login_as_admin(client, "tr-q@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        mock_data = {"pending": 3, "processing": 1, "completed": 12, "failed": 0}
        with _patch_training_httpx(mock_data):
            resp = await client.get("/api/v1/training/queue/stats", headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["pending"] == 3
        assert data["processing"] == 1

    async def test_queue_stats_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/v1/training/queue/stats")
        assert resp.status_code == 401

    async def test_queue_stats_forbidden_member(self, client: AsyncClient):
        token = await _register_and_login(client, "tr-q-mem@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/training/queue/stats", headers=headers)
        assert resp.status_code == 403


class TestTrainingCheckpoints:
    async def test_list_checkpoints_success(self, client: AsyncClient):
        token = await _register_and_login_as_admin(client, "tr-cp@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        mock_data = {"checkpoints": [{"id": "cp-1", "epoch": 3}]}
        with _patch_training_httpx(mock_data):
            resp = await client.get("/api/v1/training/checkpoints", headers=headers)

        assert resp.status_code == 200
        assert resp.json()["checkpoints"][0]["id"] == "cp-1"

    async def test_list_checkpoints_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/v1/training/checkpoints")
        assert resp.status_code == 401


class TestModelVersionsTraining:
    async def test_list_model_versions_success(self, client: AsyncClient):
        token = await _register_and_login_as_admin(client, "tr-mv@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        mock_data = {"versions": [{"name": "gpt-finetune", "version": 1}]}
        with _patch_training_httpx(mock_data):
            resp = await client.get("/api/v1/training/model/versions", headers=headers)

        assert resp.status_code == 200
        assert resp.json()["versions"][0]["name"] == "gpt-finetune"

    async def test_list_model_versions_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/v1/training/model/versions")
        assert resp.status_code == 401

    async def test_list_model_versions_forbidden_member(self, client: AsyncClient):
        token = await _register_and_login(client, "tr-mv-mem@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/training/model/versions", headers=headers)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Dataset Endpoints (/api/v1/datasets/...)
# POST requires TRAINING_WRITE (admin only)
# GET list requires BENCHMARKS_READ (viewer+)
# GET/PUT/DELETE by id require auth only (tenant-scoped)
# ---------------------------------------------------------------------------

class TestDatasetCreate:
    async def test_create_dataset_success(self, client: AsyncClient):
        token = await _register_and_login_as_admin(client, "ds-create@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/v1/datasets",
            json={
                "name": "My Test Dataset",
                "description": "Created for testing",
                "dataset_type": "synthetic",
                "num_samples": 1000,
                "num_features": 10,
                "num_classes": 5,
                "tags": ["test", "ci"],
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My Test Dataset"
        assert data["dataset_type"] == "synthetic"
        assert data["version"] == "1.0"
        assert "id" in data
        assert "created_at" in data

    async def test_create_dataset_unauthorized(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/datasets",
            json={"name": "No Auth"},
        )
        assert resp.status_code == 401

    async def test_create_dataset_forbidden_member(self, client: AsyncClient):
        token = await _register_and_login(client, "ds-create-mem@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/v1/datasets",
            json={"name": "Forbidden Dataset"},
            headers=headers,
        )
        assert resp.status_code == 403

    async def test_create_dataset_minimal_fields(self, client: AsyncClient):
        token = await _register_and_login_as_admin(client, "ds-create-min@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/v1/datasets",
            json={"name": "Minimal Dataset"},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Minimal Dataset"


class TestDatasetList:
    async def test_list_datasets_success(self, client: AsyncClient):
        token = await _register_and_login(client, "ds-list@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/datasets", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "meta" in data
        assert isinstance(data["data"], list)
        assert data["meta"]["total"] == 0

    async def test_list_datasets_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/v1/datasets")
        assert resp.status_code == 401

    async def test_list_datasets_forbidden_compliance_officer(self, client: AsyncClient):
        email = "ds-list-co@example.com"
        token = await _register_and_login(client, email)
        await _set_user_role(client, email, "compliance_officer")
        token = await _login(client, email)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/datasets", headers=headers)
        assert resp.status_code == 403

    async def test_list_datasets_with_pagination(self, client: AsyncClient):
        token = await _register_and_login(client, "ds-list-page@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/datasets?page=1&page_size=10", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["meta"]["page"] == 1

    async def test_list_datasets_after_create(self, client: AsyncClient):
        token = await _register_and_login_as_admin(client, "ds-list-cr@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            "/api/v1/datasets",
            json={"name": "Listed Dataset", "dataset_type": "real"},
            headers=headers,
        )
        assert create_resp.status_code == 201

        resp = await client.get("/api/v1/datasets", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["meta"]["total"] >= 1
        names = [d["name"] for d in resp.json()["data"]]
        assert "Listed Dataset" in names


class TestDatasetGet:
    async def test_get_dataset_success(self, client: AsyncClient):
        token = await _register_and_login_as_admin(client, "ds-get@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            "/api/v1/datasets",
            json={"name": "Fetchable Dataset"},
            headers=headers,
        )
        assert create_resp.status_code == 201
        dataset_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/datasets/{dataset_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Fetchable Dataset"
        assert data["id"] == dataset_id
        assert "created_at" in data
        assert "updated_at" in data

    async def test_get_dataset_not_found(self, client: AsyncClient):
        token = await _register_and_login(client, "ds-get-nf@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/datasets/00000000-0000-0000-0000-000000000000", headers=headers)
        assert resp.status_code == 404

    async def test_get_dataset_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/v1/datasets/some-id")
        assert resp.status_code == 401


class TestDatasetDelete:
    async def test_delete_dataset_success(self, client: AsyncClient):
        token = await _register_and_login_as_admin(client, "ds-del@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            "/api/v1/datasets",
            json={"name": "To Be Deleted"},
            headers=headers,
        )
        assert create_resp.status_code == 201
        dataset_id = create_resp.json()["id"]

        del_resp = await client.delete(f"/api/v1/datasets/{dataset_id}", headers=headers)
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "deactivated"

    async def test_delete_dataset_not_found(self, client: AsyncClient):
        token = await _register_and_login(client, "ds-del-nf@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.delete(
            "/api/v1/datasets/00000000-0000-0000-0000-000000000000",
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_delete_dataset_unauthorized(self, client: AsyncClient):
        resp = await client.delete("/api/v1/datasets/some-id")
        assert resp.status_code == 401


class TestDatasetUpdate:
    async def test_update_dataset_success(self, client: AsyncClient):
        token = await _register_and_login_as_admin(client, "ds-upd@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            "/api/v1/datasets",
            json={"name": "Original Name"},
            headers=headers,
        )
        assert create_resp.status_code == 201
        dataset_id = create_resp.json()["id"]

        upd_resp = await client.put(
            f"/api/v1/datasets/{dataset_id}",
            json={"name": "Updated Name", "num_samples": 500},
            headers=headers,
        )
        assert upd_resp.status_code == 200
        assert upd_resp.json()["status"] == "updated"

        get_resp = await client.get(f"/api/v1/datasets/{dataset_id}", headers=headers)
        assert get_resp.json()["name"] == "Updated Name"
        assert get_resp.json()["num_samples"] == 500

    async def test_update_dataset_not_found(self, client: AsyncClient):
        token = await _register_and_login(client, "ds-upd-nf@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.put(
            "/api/v1/datasets/00000000-0000-0000-0000-000000000000",
            json={"name": "Ghost"},
            headers=headers,
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Model Registry Endpoints (/api/v1/models/models/...)
# Router requires TRAINING_WRITE (admin only)
# ---------------------------------------------------------------------------

class TestModelRegistryListVersions:
    async def test_list_versions_success(self, client: AsyncClient):
        token = await _register_and_login_as_admin(client, "mreg-list@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        mock_data = {"versions": [{"name": "my-model", "version": 3}], "total": 1}
        with _patch_models_httpx(mock_data):
            resp = await client.get("/api/v1/models/models/versions", headers=headers)

        assert resp.status_code == 200
        assert resp.json()["versions"][0]["name"] == "my-model"

    async def test_list_versions_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/v1/models/models/versions")
        assert resp.status_code == 401

    async def test_list_versions_forbidden_member(self, client: AsyncClient):
        token = await _register_and_login(client, "mreg-list-mem@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/models/models/versions", headers=headers)
        assert resp.status_code == 403

    async def test_list_versions_ml_engine_error(self, client: AsyncClient):
        token = await _register_and_login_as_admin(client, "mreg-list-err@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        with _patch_models_httpx({}, status_code=503):
            resp = await client.get("/api/v1/models/models/versions", headers=headers)

        assert resp.status_code == 502

    async def test_list_versions_with_filter(self, client: AsyncClient):
        token = await _register_and_login_as_admin(client, "mreg-filter@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        mock_data = {"versions": [], "total": 0}
        with _patch_models_httpx(mock_data):
            resp = await client.get(
                "/api/v1/models/models/versions?model_name=gpt-4&limit=10",
                headers=headers,
            )

        assert resp.status_code == 200


class TestModelRegistryGetVersion:
    async def test_get_version_success(self, client: AsyncClient):
        token = await _register_and_login_as_admin(client, "mreg-get@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        mock_data = {
            "model_name": "my-model",
            "version_id": "v-42",
            "algorithm": "hybrid",
            "metrics": {"accuracy": 0.97},
        }
        with _patch_models_httpx(mock_data):
            resp = await client.get(
                "/api/v1/models/models/my-model/versions/v-42",
                headers=headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["model_name"] == "my-model"
        assert data["version_id"] == "v-42"

    async def test_get_version_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/v1/models/models/m/versions/v1")
        assert resp.status_code == 401

    async def test_get_version_forbidden_member(self, client: AsyncClient):
        token = await _register_and_login(client, "mreg-get-mem@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get(
            "/api/v1/models/models/m/versions/v1",
            headers=headers,
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Adapter Endpoints (/api/v1/adapters/...)
# Router requires ADAPTERS_WRITE (admin only)
# ---------------------------------------------------------------------------

class TestAdapterList:
    async def test_list_adapters_success(self, client: AsyncClient):
        token = await _register_and_login_as_admin(client, "ad-list@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        mock_data = {"adapters": [{"name": "lora-1", "status": "active"}]}
        with patch("app.api.v1.adapters.ml_engine_client") as mock_engine:
            mock_engine.list_adapters = AsyncMock(return_value=mock_data)
            resp = await client.get("/api/v1/adapters", headers=headers)

        assert resp.status_code == 200
        assert resp.json()["adapters"][0]["name"] == "lora-1"

    async def test_list_adapters_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/v1/adapters")
        assert resp.status_code == 401

    async def test_list_adapters_forbidden_member(self, client: AsyncClient):
        token = await _register_and_login(client, "ad-list-mem@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/adapters", headers=headers)
        assert resp.status_code == 403

    async def test_list_adapters_ml_engine_error(self, client: AsyncClient):
        token = await _register_and_login_as_admin(client, "ad-list-err@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        with patch("app.api.v1.adapters.ml_engine_client") as mock_engine:
            mock_engine.list_adapters = AsyncMock(
                side_effect=MLEngineClientError("Connection refused")
            )
            resp = await client.get("/api/v1/adapters", headers=headers)

        assert resp.status_code == 502


class TestAdapterControllerHealth:
    async def test_controller_health_success(self, client: AsyncClient):
        token = await _register_and_login_as_admin(client, "ad-ch@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        mock_data = {"status": "healthy", "uptime_seconds": 86400, "version": "1.2.0"}
        with patch("app.api.v1.adapters.ml_engine_client") as mock_engine:
            mock_engine.get_controller_health = AsyncMock(return_value=mock_data)
            resp = await client.get("/api/v1/adapters/controller/health", headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.2.0"

    async def test_controller_health_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/v1/adapters/controller/health")
        assert resp.status_code == 401

    async def test_controller_health_forbidden_member(self, client: AsyncClient):
        token = await _register_and_login(client, "ad-ch-mem@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/adapters/controller/health", headers=headers)
        assert resp.status_code == 403


class TestAdapterHealth:
    async def test_adapter_health_success(self, client: AsyncClient):
        token = await _register_and_login_as_admin(client, "ad-ah@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        mock_data = {
            "adapter_name": "lora-alpha",
            "status": "healthy",
            "active_version": "v2",
            "error_rate": 0.01,
        }
        with patch("app.api.v1.adapters.ml_engine_client") as mock_engine:
            mock_engine.get_adapter_health = AsyncMock(return_value=mock_data)
            resp = await client.get("/api/v1/adapters/lora-alpha/health", headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["adapter_name"] == "lora-alpha"
        assert data["status"] == "healthy"

    async def test_adapter_health_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/v1/adapters/lora-alpha/health")
        assert resp.status_code == 401

    async def test_adapter_health_forbidden_member(self, client: AsyncClient):
        token = await _register_and_login(client, "ad-ah-mem@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/adapters/lora-alpha/health", headers=headers)
        assert resp.status_code == 403

    async def test_adapter_health_engine_error(self, client: AsyncClient):
        token = await _register_and_login_as_admin(client, "ad-ah-err@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        with patch("app.api.v1.adapters.ml_engine_client") as mock_engine:
            mock_engine.get_adapter_health = AsyncMock(
                side_effect=MLEngineClientError("Timeout")
            )
            resp = await client.get("/api/v1/adapters/lora-alpha/health", headers=headers)

        assert resp.status_code == 502


class TestAdapterVersions:
    async def test_adapter_versions_success(self, client: AsyncClient):
        token = await _register_and_login_as_admin(client, "ad-ver@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        mock_data = {"versions": [{"id": "v1", "active": True}, {"id": "v2", "active": False}]}
        with patch("app.api.v1.adapters.ml_engine_client") as mock_engine:
            mock_engine.get_adapter_versions = AsyncMock(return_value=mock_data)
            resp = await client.get("/api/v1/adapters/lora-alpha/versions", headers=headers)

        assert resp.status_code == 200
        assert len(resp.json()["versions"]) == 2

    async def test_adapter_versions_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/v1/adapters/lora-alpha/versions")
        assert resp.status_code == 401

    async def test_adapter_versions_forbidden_member(self, client: AsyncClient):
        token = await _register_and_login(client, "ad-ver-mem@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/adapters/lora-alpha/versions", headers=headers)
        assert resp.status_code == 403


class TestAdapterRegistryStats:
    async def test_registry_stats_success(self, client: AsyncClient):
        token = await _register_and_login_as_admin(client, "ad-rs@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        mock_data = {"total_adapters": 5, "active_versions": 3, "total_versions": 10}
        with patch("app.api.v1.adapters.ml_engine_client") as mock_engine:
            mock_engine.get_registry_stats = AsyncMock(return_value=mock_data)
            resp = await client.get("/api/v1/adapters/registry/stats", headers=headers)

        assert resp.status_code == 200
        assert resp.json()["total_adapters"] == 5

    async def test_registry_stats_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/v1/adapters/registry/stats")
        assert resp.status_code == 401
