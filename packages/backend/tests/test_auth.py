import json
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from app.core.cache import cache
from app.domain.auth.entities import UserRole


class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecureP@ss123!",
                "full_name": "New User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["full_name"] == "New User"
        assert data["user"]["role"] == "member"
        assert data["user"]["is_email_verified"] is False
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_register_duplicate_email(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "dupe@example.com",
                "password": "SecureP@ss123!",
                "full_name": "First User",
            },
        )
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "dupe@example.com",
                "password": "AnotherP@ss123!",
                "full_name": "Second User",
            },
        )
        assert response.status_code == 409

    async def test_register_with_tenant_slug(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "tenantuser@example.com",
                "password": "SecureP@ss123!",
                "full_name": "Tenant User",
                "tenant_slug": "my-custom-tenant",
            },
        )
        assert response.status_code == 201
        assert response.json()["user"]["email"] == "tenantuser@example.com"

    async def test_register_invalid_email(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecureP@ss123!",
                "full_name": "Bad Email",
            },
        )
        assert response.status_code == 422

    async def test_register_missing_fields(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com"},
        )
        assert response.status_code == 422


class TestEmailVerification:
    async def test_verify_email(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "verify@example.com",
                "password": "SecureP@ss123!",
                "full_name": "Verify Me",
            },
        )
        cache_keys = list(cache.redis._store.keys())
        verify_key = next(k for k in cache_keys if k.startswith("verify:email:"))
        token = verify_key.split("verify:email:")[1]

        response = await client.post(
            "/api/v1/auth/verify-email",
            json={"token": token},
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Email verified successfully"

        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "verify@example.com",
                "password": "SecureP@ss123!",
            },
        )
        access_token = login_resp.json()["access_token"]
        me_resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["is_email_verified"] is True

    async def test_verify_email_invalid_token(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/verify-email",
            json={"token": "invalid-token-that-does-not-exist"},
        )
        assert response.status_code == 401


class TestLogin:
    async def test_login_success(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "login-test@example.com",
                "password": "SecureP@ss123!",
                "full_name": "Login Test",
            },
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "login-test@example.com",
                "password": "SecureP@ss123!",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "wrongpass@example.com",
                "password": "SecureP@ss123!",
                "full_name": "Wrong Pass",
            },
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "wrongpass@example.com",
                "password": "WrongPassword123!",
            },
        )
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "noone@example.com",
                "password": "AnyPassword123!",
            },
        )
        assert response.status_code == 401

    async def test_login_account_lockout(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "lockout@example.com",
                "password": "SecureP@ss123!",
                "full_name": "Lockout Test",
            },
        )
        for _ in range(5):
            await client.post(
                "/api/v1/auth/login",
                json={
                    "email": "lockout@example.com",
                    "password": "WrongPassword123!",
                },
            )
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "lockout@example.com",
                "password": "WrongPassword123!",
            },
        )
        assert response.status_code == 401


class TestTokenRefresh:
    async def test_refresh_token(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "refresh@example.com",
                "password": "SecureP@ss123!",
                "full_name": "Refresh Test",
            },
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "refresh@example.com",
                "password": "SecureP@ss123!",
            },
        )
        old_refresh = login_resp.json()["refresh_token"]
        old_access = login_resp.json()["access_token"]

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

        old_me = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {old_access}"},
        )
        assert old_me.status_code == 200

        new_me = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {data['access_token']}"},
        )
        assert new_me.status_code == 200

    async def test_refresh_with_revoked_token(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "refresh-revoke@example.com",
                "password": "SecureP@ss123!",
                "full_name": "Refresh Revoke",
            },
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "refresh-revoke@example.com",
                "password": "SecureP@ss123!",
            },
        )
        refresh_token = login_resp.json()["refresh_token"]

        await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 401

    async def test_refresh_invalid_token(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "this-is-completely-invalid"},
        )
        assert response.status_code == 401


class TestLogout:
    async def test_logout(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "logout@example.com",
                "password": "SecureP@ss123!",
                "full_name": "Logout Test",
            },
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "logout@example.com",
                "password": "SecureP@ss123!",
            },
        )
        access_token = login_resp.json()["access_token"]
        refresh_token = login_resp.json()["refresh_token"]

        response = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token, "all_sessions": False},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200

        me_resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_resp.status_code == 401

    async def test_logout_all_sessions(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "logout-all@example.com",
                "password": "SecureP@ss123!",
                "full_name": "Logout All",
            },
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "logout-all@example.com",
                "password": "SecureP@ss123!",
            },
        )
        access_token = login_resp.json()["access_token"]

        response = await client.post(
            "/api/v1/auth/logout",
            json={"all_sessions": True},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200


class TestPasswordReset:
    async def test_forgot_password(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "forgot@example.com",
                "password": "SecureP@ss123!",
                "full_name": "Forgot Test",
            },
        )
        response = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "forgot@example.com"},
        )
        assert response.status_code == 200
        assert "sent" in response.json()["message"]

    async def test_forgot_password_nonexistent(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "noone@example.com"},
        )
        assert response.status_code == 200

    async def test_reset_password(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "reset@example.com",
                "password": "OldP@ss123!",
                "full_name": "Reset Test",
            },
        )
        await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "reset@example.com"},
        )

        cache_keys = list(cache.redis._store.keys())
        reset_key = next(k for k in cache_keys if k.startswith("reset:password:"))
        token = reset_key.split("reset:password:")[1]

        response = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "password": "NewP@ss123!"},
        )
        assert response.status_code == 200

        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "reset@example.com",
                "password": "NewP@ss123!",
            },
        )
        assert login_resp.status_code == 200

        old_login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "reset@example.com",
                "password": "OldP@ss123!",
            },
        )
        assert old_login.status_code == 401

    async def test_reset_password_invalid_token(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": "bad-token", "password": "NewP@ss123!"},
        )
        assert response.status_code == 401


class TestChangePassword:
    async def test_change_password_success(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "changepw@example.com",
                "password": "OldP@ss123!",
                "full_name": "Change PW",
            },
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "changepw@example.com",
                "password": "OldP@ss123!",
            },
        )
        access_token = login_resp.json()["access_token"]

        response = await client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "OldP@ss123!",
                "new_password": "NewP@ss123!",
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200

        new_login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "changepw@example.com",
                "password": "NewP@ss123!",
            },
        )
        assert new_login.status_code == 200

    async def test_change_password_wrong_current(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "wrongcpw@example.com",
                "password": "SecureP@ss123!",
                "full_name": "Wrong CPW",
            },
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "wrongcpw@example.com",
                "password": "SecureP@ss123!",
            },
        )
        access_token = login_resp.json()["access_token"]

        response = await client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "WrongPassword123!",
                "new_password": "NewP@ss123!",
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 401


class TestProfile:
    async def test_get_me(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "profile@example.com",
                "password": "SecureP@ss123!",
                "full_name": "Profile Test",
            },
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "profile@example.com",
                "password": "SecureP@ss123!",
            },
        )
        access_token = login_resp.json()["access_token"]

        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "profile@example.com"
        assert data["full_name"] == "Profile Test"
        assert "id" in data
        assert "role" in data

    async def test_get_me_unauthorized(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401


class TestUsersProfile:
    async def _get_auth_headers(self, client: AsyncClient, email: str) -> dict:
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "SecureP@ss123!"},
        )
        token = login_resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    async def test_update_profile(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "update@example.com",
                "password": "SecureP@ss123!",
                "full_name": "Original Name",
            },
        )
        headers = await self._get_auth_headers(client, "update@example.com")

        response = await client.patch(
            "/api/v1/users/me",
            json={"full_name": "Updated Name"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["full_name"] == "Updated Name"

        me_resp = await client.get(
            "/api/v1/auth/me",
            headers=headers,
        )
        assert me_resp.json()["full_name"] == "Updated Name"

    async def test_get_sessions(self, client: AsyncClient):
        email = "sessions-test@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "SecureP@ss123!",
                "full_name": "Sessions Test",
            },
        )
        await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "SecureP@ss123!"},
        )
        headers = await self._get_auth_headers(client, email)

        response = await client.get(
            "/api/v1/users/me/sessions",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) >= 1
        assert "id" in data["data"][0]
        assert "is_current" in data["data"][0]

    async def test_revoke_session(self, client: AsyncClient):
        email = "revoke-session@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "SecureP@ss123!",
                "full_name": "Revoke Session",
            },
        )
        headers = await self._get_auth_headers(client, email)

        sessions_resp = await client.get(
            "/api/v1/users/me/sessions",
            headers=headers,
        )
        session_id = sessions_resp.json()["data"][0]["id"]

        response = await client.delete(
            f"/api/v1/users/me/sessions/{session_id}",
            headers=headers,
        )
        assert response.status_code == 200

    async def test_revoke_all_sessions(self, client: AsyncClient):
        email = "revoke-all@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "SecureP@ss123!",
                "full_name": "Revoke All",
            },
        )
        headers = await self._get_auth_headers(client, email)

        response = await client.delete(
            "/api/v1/users/me/sessions",
            headers=headers,
        )
        assert response.status_code == 200


class TestOAuth:
    async def test_oauth_google_url(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/oauth/google")
        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "accounts.google.com" in data["authorization_url"]
        assert "test-id" in data["authorization_url"]

    async def test_oauth_github_url(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/oauth/github")
        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "github.com" in data["authorization_url"]

    async def test_oauth_unsupported_provider(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/oauth/twitter")
        assert response.status_code == 400


class TestApiKeyManagement:
    async def _register_and_login(self, client: AsyncClient) -> str:
        email = "apikey-mgr@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "SecureP@ss123!", "full_name": "API Key Mgr"},
        )

        from app.core.database import db
        async with db.session_factory() as session:
            from app.infrastructure.database.models import UserModel
            from sqlalchemy import select, update
            result = await session.execute(select(UserModel).where(UserModel.email == email))
            user = result.scalar_one_or_none()
            if user:
                user.role = "admin"
                await session.commit()

        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "SecureP@ss123!"},
        )
        return resp.json()["access_token"]

    async def test_create_api_key(self, client: AsyncClient):
        token = await self._register_and_login(client)
        response = await client.post(
            "/api/v1/auth/api-keys",
            json={"name": "Test Key", "scopes": ["read", "write"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Key"
        assert data["scopes"] == ["read", "write"]
        assert "raw_key" in data
        assert data["raw_key"].startswith("vu_")

    async def test_list_api_keys(self, client: AsyncClient):
        token = await self._register_and_login(client)
        await client.post(
            "/api/v1/auth/api-keys",
            json={"name": "Key 1", "scopes": ["read"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        await client.post(
            "/api/v1/auth/api-keys",
            json={"name": "Key 2", "scopes": ["write"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        response = await client.get(
            "/api/v1/auth/api-keys",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2

    async def test_revoke_api_key(self, client: AsyncClient):
        token = await self._register_and_login(client)
        create_resp = await client.post(
            "/api/v1/auth/api-keys",
            json={"name": "Revocable Key", "scopes": ["read"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        key_id = create_resp.json()["id"]

        response = await client.delete(
            f"/api/v1/auth/api-keys/{key_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        list_resp = await client.get(
            "/api/v1/auth/api-keys",
            headers={"Authorization": f"Bearer {token}"},
        )
        keys = list_resp.json()["data"]
        revoked = next(k for k in keys if k["id"] == key_id)
        assert revoked["is_active"] is False


class TestApiKeyAuth:
    async def test_authenticate_with_api_key(self, client: AsyncClient):
        token = await self._register_and_login_api(client)
        create_resp = await client.post(
            "/api/v1/auth/api-keys",
            json={"name": "Auth Test Key", "scopes": ["*"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        raw_key = create_resp.json()["raw_key"]

        response = await client.get(
            "/api/v1/auth/me",
            headers={"X-API-Key": raw_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "apikey-auth-test@example.com"

    async def test_invalid_api_key(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/auth/me",
            headers={"X-API-Key": "vu_invalid_key_that_does_not_exist"},
        )
        assert response.status_code == 401

    @staticmethod
    async def _register_and_login_api(client: AsyncClient) -> str:
        email = "apikey-auth-test@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "SecureP@ss123!", "full_name": "API Key Auth"},
        )

        from app.core.database import db
        async with db.session_factory() as session:
            from app.infrastructure.database.models import UserModel
            from sqlalchemy import select
            result = await session.execute(select(UserModel).where(UserModel.email == email))
            user = result.scalar_one_or_none()
            if user:
                user.role = "admin"
                await session.commit()

        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "SecureP@ss123!"},
        )
        return resp.json()["access_token"]


class TestMFA:
    async def _get_auth_headers(self, client: AsyncClient, email: str = "mfa-test@example.com") -> dict:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "SecureP@ss123!"},
        )
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    async def test_totp_setup(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "mfa-test@example.com", "password": "SecureP@ss123!", "full_name": "MFA Test"},
        )
        headers = await self._get_auth_headers(client)
        response = await client.post(
            "/api/v1/auth/mfa/totp/setup",
            json={"password": "SecureP@ss123!"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "secret" in data
        assert "provisioning_uri" in data
        assert len(data["secret"]) > 10

    async def test_totp_setup_wrong_password(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "mfa-wrongpw@example.com", "password": "SecureP@ss123!", "full_name": "MFA Wrong"},
        )
        headers = await self._get_auth_headers(client, "mfa-wrongpw@example.com")
        response = await client.post(
            "/api/v1/auth/mfa/totp/setup",
            json={"password": "WrongPassword123!"},
            headers=headers,
        )
        assert response.status_code == 401

    async def test_totp_enable_and_login_challenge(self, client: AsyncClient):
        import pyotp

        await client.post(
            "/api/v1/auth/register",
            json={"email": "mfa-enable@example.com", "password": "SecureP@ss123!", "full_name": "MFA Enable"},
        )
        headers = await self._get_auth_headers(client, "mfa-enable@example.com")

        setup_resp = await client.post(
            "/api/v1/auth/mfa/totp/setup",
            json={"password": "SecureP@ss123!"},
            headers=headers,
        )
        secret = setup_resp.json()["secret"]

        totp = pyotp.TOTP(secret)
        valid_code = totp.now()

        enable_resp = await client.post(
            "/api/v1/auth/mfa/totp/enable",
            json={"secret": secret, "code": valid_code},
            headers=headers,
        )
        assert enable_resp.status_code == 200
        assert enable_resp.json()["message"] == "MFA enabled successfully"

        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "mfa-enable@example.com", "password": "SecureP@ss123!"},
        )
        assert login_resp.status_code == 200
        login_data = login_resp.json()
        assert login_data.get("mfa_required") is True
        assert "challenge_token" in login_data

        challenge_token = login_data["challenge_token"]

        verify_resp = await client.post(
            "/api/v1/auth/mfa/verify",
            json={"challenge_token": challenge_token, "code": totp.now()},
        )
        assert verify_resp.status_code == 200
        verify_data = verify_resp.json()
        assert "access_token" in verify_data
        assert "refresh_token" in verify_data

    async def test_mfa_verify_invalid_code(self, client: AsyncClient):
        import pyotp

        await client.post(
            "/api/v1/auth/register",
            json={"email": "mfa-badcode@example.com", "password": "SecureP@ss123!", "full_name": "MFA Bad Code"},
        )
        headers = await self._get_auth_headers(client, "mfa-badcode@example.com")

        setup_resp = await client.post(
            "/api/v1/auth/mfa/totp/setup",
            json={"password": "SecureP@ss123!"},
            headers=headers,
        )
        secret = setup_resp.json()["secret"]
        totp = pyotp.TOTP(secret)

        await client.post(
            "/api/v1/auth/mfa/totp/enable",
            json={"secret": secret, "code": totp.now()},
            headers=headers,
        )

        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "mfa-badcode@example.com", "password": "SecureP@ss123!"},
        )
        challenge_token = login_resp.json()["challenge_token"]

        verify_resp = await client.post(
            "/api/v1/auth/mfa/verify",
            json={"challenge_token": challenge_token, "code": "000000"},
        )
        assert verify_resp.status_code == 401

    async def test_mfa_verify_expired_challenge(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "mfa-expired@example.com", "password": "SecureP@ss123!", "full_name": "MFA Expired"},
        )
        headers = await self._get_auth_headers(client, "mfa-expired@example.com")

        response = await client.post(
            "/api/v1/auth/mfa/verify",
            json={"challenge_token": "nonexistent-token", "code": "123456"},
        )
        assert response.status_code == 401

    async def test_totp_disable(self, client: AsyncClient):
        import pyotp

        await client.post(
            "/api/v1/auth/register",
            json={"email": "mfa-disable@example.com", "password": "SecureP@ss123!", "full_name": "MFA Disable"},
        )
        headers = await self._get_auth_headers(client, "mfa-disable@example.com")

        setup_resp = await client.post(
            "/api/v1/auth/mfa/totp/setup",
            json={"password": "SecureP@ss123!"},
            headers=headers,
        )
        secret = setup_resp.json()["secret"]
        totp = pyotp.TOTP(secret)

        await client.post(
            "/api/v1/auth/mfa/totp/enable",
            json={"secret": secret, "code": totp.now()},
            headers=headers,
        )

        code = totp.now()
        disable_resp = await client.post(
            "/api/v1/auth/mfa/totp/disable",
            json={"code": code},
            headers=headers,
        )
        assert disable_resp.status_code == 200
        assert disable_resp.json()["message"] == "MFA disabled successfully"

        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "mfa-disable@example.com", "password": "SecureP@ss123!"},
        )
        assert login_resp.status_code == 200
        assert "access_token" in login_resp.json()

    async def test_mfa_unauthorized_without_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/mfa/totp/setup",
            json={"password": "test"},
        )
        assert response.status_code == 401


class TestJTIBlacklist:
    async def test_blacklisted_jti_returns_401(self, client: AsyncClient):
        from app.core.cache import cache

        await client.post(
            "/api/v1/auth/register",
            json={"email": "blacklist@example.com", "password": "SecureP@ss123!", "full_name": "Blacklist Test"},
        )
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "blacklist@example.com", "password": "SecureP@ss123!"},
        )
        access_token = resp.json()["access_token"]

        me_resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_resp.status_code == 200

        from app.core.security import token_manager
        payload = token_manager.decode_token(access_token)
        jti = payload["jti"]
        await cache.set(f"jti:blacklist:{jti}", True)

        me_resp2 = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_resp2.status_code == 401
