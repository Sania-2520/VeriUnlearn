import pytest
from app.core.security import hash_password, verify_password, token_manager


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "SecureP@ss123!"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed)

    def test_wrong_password_fails(self):
        password = "SecureP@ss123!"
        hashed = hash_password(password)
        assert not verify_password("WrongPassword", hashed)

    def test_different_hashes_for_same_password(self):
        password = "SecureP@ss123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2


class TestTokenManager:
    def test_create_access_token(self):
        token = token_manager.create_access_token(subject="user123")
        assert token is not None
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

    def test_verify_valid_token(self):
        token = token_manager.create_access_token(
            subject="user123",
            extra_claims={"role": "admin", "tenant_id": "tenant1"},
        )
        payload = token_manager.verify_token(token, expected_type="access")
        assert payload["sub"] == "user123"
        assert payload["role"] == "admin"
        assert payload["type"] == "access"

    def test_verify_invalid_token(self):
        with pytest.raises(Exception):
            token_manager.verify_token("invalid.token.here")

    def test_verify_expired_token(self):
        import time
        from datetime import timedelta

        token = token_manager.create_access_token(
            subject="user123",
            expires_delta=timedelta(seconds=-1),
        )
        with pytest.raises(Exception):
            token_manager.verify_token(token)

    def test_refresh_token_type_check(self):
        refresh = token_manager.create_refresh_token(subject="user123")
        with pytest.raises(Exception, match="Invalid token type"):
            token_manager.verify_token(refresh, expected_type="access")

    def test_generate_token_hash(self):
        raw, hashed = token_manager.generate_token_hash()
        assert raw is not None
        assert hashed is not None
        assert raw != hashed
        assert token_manager.hash_token(raw) == hashed
