import pytest
from app.core.config import Settings, Environment

_VALID_SECRET = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
_VALID_JWT = "jwt-a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"


def _settings(**kwargs):
    overrides = {"secret_key": _VALID_SECRET, "jwt_secret_key": _VALID_JWT}
    overrides.update(kwargs)
    return Settings(**overrides)


class TestSettings:
    def test_default_environment(self, monkeypatch):
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        s = _settings()
        assert s.environment == Environment.DEVELOPMENT

    def test_is_development(self):
        s = _settings(environment="development")
        assert s.is_development
        assert not s.is_production

    def test_testing_environment(self):
        s = _settings(environment="testing")
        assert s.environment == Environment.TESTING
        assert not s.is_development
        assert not s.is_production

    def test_is_production(self):
        s = _settings(environment="production")
        assert s.is_production
        assert not s.is_development

    def test_cors_origins_list(self):
        s = _settings(cors_origins="http://localhost:3000,https://app.example.com")
        assert "http://localhost:3000" in s.cors_origins_list
        assert "https://app.example.com" in s.cors_origins_list
        assert len(s.cors_origins_list) == 2

    def test_allowed_upload_types_list(self):
        s = _settings(allowed_upload_types="image/jpeg,image/png,application/pdf")
        assert "image/jpeg" in s.allowed_upload_types_list
        assert "application/pdf" in s.allowed_upload_types_list
        assert len(s.allowed_upload_types_list) == 3

    def test_max_upload_size_bytes(self):
        s = _settings(max_upload_size_mb=50)
        assert s.max_upload_size_bytes == 50 * 1024 * 1024

    def test_gpu_devices_list(self):
        s = _settings(ml_gpu_devices="0,1,2")
        assert s.ml_gpu_devices_list == [0, 1, 2]

    def test_secret_key_rejects_placeholder(self):
        with pytest.raises(Exception):
            Settings(secret_key="change-me")

    def test_allowed_hosts_list_from_single_domain(self):
        s = _settings(allowed_hosts="")
        assert "localhost:3000" in s.allowed_hosts_list

    def test_allowed_hosts_list_from_csv(self):
        s = _settings(allowed_hosts="api.veriunlearn.com,app.veriunlearn.com")
        assert "api.veriunlearn.com" in s.allowed_hosts_list
        assert len(s.allowed_hosts_list) == 2
