import pyotp
import pytest
from app.core.database import db
from app.infrastructure.database.models import UserModel
from httpx import AsyncClient
from sqlalchemy import update


async def _register_and_login(client: AsyncClient, email: str, password: str = "SecureP@ss123!") -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": email.split("@")[0]},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    data = resp.json()
    return data.get("access_token", "")


async def _set_user_role(email: str, role: str) -> None:
    async with db.session_factory() as session:
        await session.execute(
            update(UserModel).where(UserModel.email == email).values(role=role)
        )
        await session.commit()


class TestRBAC:
    @pytest.mark.parametrize("role,allowed_endpoints", [
        ("viewer", [
            ("GET", "/api/v1/unlearning/requests", None),
            ("GET", "/api/v1/memory", None),
        ]),
        ("member", [
            ("GET", "/api/v1/chat/sessions", None),
            ("GET", "/api/v1/unlearning/requests", None),
            ("GET", "/api/v1/users/me", None),
            ("GET", "/api/v1/providers", None),
        ]),
        ("unlearning_auditor", [
            ("GET", "/api/v1/unlearning/requests", None),
            ("POST", "/api/v1/unlearning/requests/test-id/retry", {404}),
        ]),
        ("compliance_officer", [
            ("GET", "/api/v1/compliance/reports/test-id", {400, 404}),
            ("GET", "/api/v1/security/assessments/test-id", {400, 404}),
        ]),
        ("admin", [
            ("GET", "/api/v1/admin/users", None),
            ("GET", "/api/v1/admin/gpu-metrics", {400, 404}),
            ("GET", "/api/v1/admin/jobs", {400, 404}),
        ]),
    ])
    async def test_role_allowed_endpoints(self, client: AsyncClient, role: str, allowed_endpoints: list):
        email = f"rbac-allow-{role}@example.com"
        await _register_and_login(client, email)
        await _set_user_role(email, role)
        token = (await client.post("/api/v1/auth/login", json={"email": email, "password": "SecureP@ss123!"})).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        for method, path, extra_statuses in allowed_endpoints:
            kwargs = {"headers": headers}
            if method == "POST":
                kwargs["json"] = {}
            resp = await client.request(method, path, **kwargs)
            expected = {200, 201, 202}
            if extra_statuses:
                expected = expected.union(extra_statuses)
            assert resp.status_code in expected, f"{role} should access {method} {path} but got {resp.status_code}"

    @pytest.mark.parametrize("role,denied_endpoints", [
        ("viewer", [
            ("GET", "/api/v1/admin/users"),
            ("GET", "/api/v1/users/me"),
        ]),
        ("member", [
            ("GET", "/api/v1/admin/users"),
        ]),
        ("unlearning_auditor", [
            ("GET", "/api/v1/admin/users"),
            ("PUT", "/api/v1/compliance/settings"),
        ]),
        ("compliance_officer", [
            ("POST", "/api/v1/auth/api-keys"),
        ]),
    ])
    async def test_role_denied_endpoints(self, client: AsyncClient, role: str, denied_endpoints: list):
        email = f"rbac-deny-{role}@example.com"
        await _register_and_login(client, email)
        await _set_user_role(email, role)
        token = (await client.post("/api/v1/auth/login", json={"email": email, "password": "SecureP@ss123!"})).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        for method, path in denied_endpoints:
            kwargs = {"headers": headers}
            if method in ("POST", "PUT"):
                kwargs["json"] = {}
            resp = await client.request(method, path, **kwargs)
            assert resp.status_code == 403, f"{role} should be denied {method} {path} but got {resp.status_code}"

    async def test_viewer_cannot_access_admin(self, client: AsyncClient):
        email = "rbac-viewer-admin@example.com"
        await _register_and_login(client, email)
        await _set_user_role(email, "viewer")
        token = (await client.post("/api/v1/auth/login", json={"email": email, "password": "SecureP@ss123!"})).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/admin/users", headers=headers)
        assert resp.status_code == 403

    async def test_admin_can_access_all(self, client: AsyncClient):
        email = "rbac-admin-all@example.com"
        await _register_and_login(client, email)
        await _set_user_role(email, "admin")
        token = (await client.post("/api/v1/auth/login", json={"email": email, "password": "SecureP@ss123!"})).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        endpoints = [
            ("GET", "/api/v1/admin/users"),
            ("GET", "/api/v1/audit/events"),
            ("GET", "/api/v1/compliance/settings"),
            ("GET", "/api/v1/unlearning/requests"),
            ("POST", "/api/v1/auth/api-keys"),
        ]
        for method, path in endpoints:
            kwargs = {"headers": headers}
            if method == "POST":
                kwargs["json"] = {"name": "test", "scopes": ["*"]}
            resp = await client.request(method, path, **kwargs)
            assert resp.status_code in (200, 201), f"admin should access {method} {path} but got {resp.status_code}"

    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.get("/api/v1/chat/sessions")
        assert resp.status_code == 401
        resp = await client.post("/api/v1/unlearning/requests", json={})
        assert resp.status_code == 401
        resp = await client.get("/api/v1/admin/users")
        assert resp.status_code == 401


class TestRateLimiting:
    async def test_rate_limit_exceeded_returns_429(self, client: AsyncClient):
        from app.core.rate_limiter import _default_limiter
        original_window = _default_limiter.window_seconds
        original_max = _default_limiter.max_requests
        _default_limiter.window_seconds = 60
        _default_limiter.max_requests = 3

        try:
            email = "ratelimit-test@example.com"
            await client.post(
                "/api/v1/auth/register",
                json={"email": email, "password": "SecureP@ss123!", "full_name": "Rate Limit"},
            )
            resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "SecureP@ss123!"})
            token = resp.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            for i in range(3):
                resp = await client.get("/api/v1/chat/sessions", headers=headers)
                assert resp.status_code == 200, f"request {i+1} should succeed"

            resp = await client.get("/api/v1/chat/sessions", headers=headers)
            assert resp.status_code == 429
            assert "X-RateLimit-Limit" in resp.headers
            assert "X-RateLimit-Remaining" in resp.headers
            assert "X-RateLimit-Reset" in resp.headers
        finally:
            _default_limiter.window_seconds = original_window
            _default_limiter.max_requests = original_max

    async def test_member_role_cannot_access_admin_users(self, client: AsyncClient):
        email = "member-admin-deny@example.com"
        await _register_and_login(client, email)
        token = (await client.post("/api/v1/auth/login", json={"email": email, "password": "SecureP@ss123!"})).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/admin/users", headers=headers)
        assert resp.status_code == 403


class TestMFAEnforcement:
    async def _setup_mfa(self, client: AsyncClient, email: str) -> dict:
        await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "SecureP@ss123!", "full_name": email.split("@")[0]},
        )
        from app.core.database import db
        from app.infrastructure.database.models import UserModel
        from sqlalchemy import update
        async with db.session_factory() as session:
            await session.execute(
                update(UserModel).where(UserModel.email == email).values(role="admin")
            )
            await session.commit()
        resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "SecureP@ss123!"})
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        setup_resp = await client.post("/api/v1/auth/mfa/totp/setup", json={"password": "SecureP@ss123!"}, headers=headers)
        secret = setup_resp.json()["secret"]
        totp = pyotp.TOTP(secret)
        await client.post("/api/v1/auth/mfa/totp/enable", json={"secret": secret, "code": totp.now()}, headers=headers)
        return {"token": token, "headers": headers, "totp": totp}

    async def test_change_password_blocked_when_mfa_enabled(self, client: AsyncClient):
        ctx = await self._setup_mfa(client, "mfa-cp-block@example.com")
        resp = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "SecureP@ss123!", "new_password": "NewP@ss123!"},
            headers=ctx["headers"],
        )
        assert resp.status_code == 403
        assert "MFA" in resp.json()["detail"]

    async def test_api_key_create_blocked_when_mfa_enabled(self, client: AsyncClient):
        ctx = await self._setup_mfa(client, "mfa-key-block@example.com")
        resp = await client.post(
            "/api/v1/auth/api-keys",
            json={"name": "Test Key", "scopes": ["*"]},
            headers=ctx["headers"],
        )
        assert resp.status_code == 403
        assert "MFA" in resp.json()["detail"]

    async def test_endpoints_without_mfa_enforcement_still_work(self, client: AsyncClient):
        ctx = await self._setup_mfa(client, "mfa-noenf@example.com")

        resp = await client.get("/api/v1/auth/me", headers=ctx["headers"])
        assert resp.status_code == 200

        resp = await client.get("/api/v1/users/me", headers=ctx["headers"])
        assert resp.status_code == 200

    async def test_mfa_verified_token_bypasses_require_mfa(self, client: AsyncClient):
        email = "mfa-post-challenge@example.com"
        ctx = await self._setup_mfa(client, email)

        resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "SecureP@ss123!"})
        challenge_token = resp.json()["challenge_token"]

        verify_resp = await client.post(
            "/api/v1/auth/mfa/verify",
            json={"challenge_token": challenge_token, "code": ctx["totp"].now()},
        )
        assert verify_resp.status_code == 200
        new_token = verify_resp.json()["access_token"]
        new_headers = {"Authorization": f"Bearer {new_token}"}

        resp = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "SecureP@ss123!", "new_password": "NewP@ss123!"},
            headers=new_headers,
        )
        assert resp.status_code == 200
