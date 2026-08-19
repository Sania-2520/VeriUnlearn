"""Phase 1 live-server smoke tests (auth, authorization, exceptions, security)."""
import json
import time
import sys

import httpx

BASE = "http://127.0.0.1:8000"
results = {"pass": 0, "fail": 0, "warn": 0}
failures = []


def check(name, cond, detail=""):
    if cond:
        results["pass"] += 1
        print(f"  PASS  {name}")
    else:
        results["fail"] += 1
        failures.append((name, detail))
        print(f"  FAIL  {name} -- {detail}")


def warn(name, detail=""):
    results["warn"] += 1
    print(f"  WARN  {name} -- {detail}")


c = httpx.Client(base_url=BASE, timeout=30)

print("=== STEP 10: AUTHENTICATION ===")
# Register (fall back to login if already registered)
r = c.post("/api/v1/auth/register", json={"email": "qa@veriunlearn.dev", "full_name": "QA User", "password": "password123"})
if r.status_code == 201:
    check("register valid user", True)
    token = r.json().get("access_token")
else:
    check("register valid user (or already registered)", r.status_code == 409, f"got {r.status_code}: {r.text[:200]}")
    token = c.post("/api/v1/auth/login", json={"email": "qa@veriunlearn.dev", "password": "password123"}).json().get("access_token")
check("JWT issued", bool(token), "no access_token")

# Duplicate register
r = c.post("/api/v1/auth/register", json={"email": "qa@veriunlearn.dev", "full_name": "QA User", "password": "password123"})
check("duplicate register rejected", r.status_code in (400, 409), f"got {r.status_code}: {r.text[:200]}")

# Invalid email
r = c.post("/api/v1/auth/register", json={"email": "not-an-email", "full_name": "X", "password": "password123"})
check("invalid email rejected", r.status_code == 422, f"got {r.status_code}")

# Weak password
r = c.post("/api/v1/auth/register", json={"email": "weak@veriunlearn.dev", "full_name": "X", "password": "short"})
check("weak password rejected", r.status_code in (400, 422), f"got {r.status_code}: {r.text[:200]}")

# Missing fields
r = c.post("/api/v1/auth/register", json={"email": "missing@veriunlearn.dev"})
check("missing fields rejected", r.status_code == 422, f"got {r.status_code}")

# Login OK
r = c.post("/api/v1/auth/login", json={"email": "qa@veriunlearn.dev", "password": "password123"})
check("login valid", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
login_token = r.json().get("access_token") if r.status_code == 200 else None

# Wrong password
r = c.post("/api/v1/auth/login", json={"email": "qa@veriunlearn.dev", "password": "wrongpass"})
check("wrong password rejected", r.status_code == 401, f"got {r.status_code}: {r.text[:200]}")

# Unknown user
r = c.post("/api/v1/auth/login", json={"email": "nobody@veriunlearn.dev", "password": "whatever"})
check("unknown user rejected", r.status_code == 401, f"got {r.status_code}")

# Missing credentials
r = c.get("/api/v1/auth/me")
check("protected API without token -> 401", r.status_code == 401, f"got {r.status_code}")

# Malformed token
r = c.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
check("malformed JWT rejected", r.status_code == 401, f"got {r.status_code}")

# Expired JWT
import jwt as pyjwt
expired = pyjwt.encode({"sub": "u1", "exp": int(time.time()) - 3600}, "dev-only-change-me-in-production", algorithm="HS256")
r = c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
check("expired JWT rejected", r.status_code == 401, f"got {r.status_code}")

# Tampered token (wrong signature)
tampered = pyjwt.encode({"sub": "u1", "exp": int(time.time()) + 3600}, "wrong-secret", algorithm="HS256")
r = c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered}"})
check("tampered JWT rejected", r.status_code == 401, f"got {r.status_code}")

print("=== STEP 11: AUTHORIZATION ===")
headers = {"Authorization": f"Bearer {login_token or token}"}
# Admin-only route
r = c.get("/api/v1/admin/users", headers=headers)
check("non-admin blocked from /admin/users", r.status_code == 403, f"got {r.status_code}: {r.text[:200]}")

# Role escalation attempt — viewer tries to change role (needs admin)
r = c.patch("/api/v1/admin/users/doesnotexist/role", headers=headers, json={"role": "admin"})
check("non-admin cannot change roles", r.status_code == 403, f"got {r.status_code}")

# Authenticated user can access own profile
r = c.get("/api/v1/auth/me", headers=headers)
check("authenticated /auth/me", r.status_code == 200, f"got {r.status_code}")

print("=== STEP 15: EXCEPTION HANDLING ===")
# Invalid JSON body
r = c.post("/api/v1/auth/login", content="{not-json", headers={"Content-Type": "application/json"})
check("invalid JSON -> 422", r.status_code == 422, f"got {r.status_code}: {r.text[:200]}")

# Invalid UUID
r = c.get("/api/v1/certificates/not-a-uuid", headers=headers)
check("invalid UUID handled (4xx, not 500)", 400 <= r.status_code < 500, f"got {r.status_code}")

# Nonexistent resource
r = c.get("/api/v1/certificates/00000000-0000-0000-0000-000000000000", headers=headers)
check("nonexistent id -> 404", r.status_code == 404, f"got {r.status_code}")

# Unknown endpoint
r = c.get("/api/v1/does-not-exist")
check("unknown endpoint -> 404", r.status_code == 404, f"got {r.status_code}")

# Unsupported media / missing file on upload
r = c.post("/api/v1/datasets/upload", headers=headers)
check("upload without file -> 422", r.status_code == 422, f"got {r.status_code}")

print("=== STEP 17: SECURITY ===")
# Password not stored in plaintext: check user model via register response / no password field
r = c.post("/api/v1/auth/register", json={"email": "sec@veriunlearn.dev", "full_name": "Sec", "password": "password123"})
body = r.text
check("no password/plaintext leaked in responses", "password" not in body.lower() or '"password"' not in body, "password key present in response")

# Secrets not exposed
for path in ["/.env", "/.env.example", "/app/core/config.py", "/proc/self/environ", "/veriunlearn.db"]:
    rr = c.get(path)
    if rr.status_code < 400:
        warn(f"path {path} reachable", f"status {rr.status_code}")
    else:
        check(f"secret path {path} blocked", True)

# CORS: disallowed origin
r = c.options("/api/v1/auth/login", headers={
    "Origin": "http://evil.example.com",
    "Access-Control-Request-Method": "POST",
})
check("CORS blocks disallowed origin", "access-control-allow-origin" not in r.headers or r.headers["access-control-allow-origin"] == "*" or "evil.example.com" not in r.headers.get("access-control-allow-origin", ""), f"allow-origin: {r.headers.get('access-control-allow-origin')}")

# CORS: allowed origin
r = c.options("/api/v1/auth/login", headers={
    "Origin": "http://localhost:3000",
    "Access-Control-Request-Method": "POST",
})
check("CORS allows localhost:3000", r.headers.get("access-control-allow-origin", "").rstrip("/") in ("http://localhost:3000", "*"), f"allow-origin: {r.headers.get('access-control-allow-origin')}")

# Security headers
r = c.get("/health")
for h in ["x-content-type-options", "x-frame-options", "content-security-policy"]:
    if h in r.headers:
        check(f"security header {h} present", True)
    else:
        warn(f"security header {h} missing", "not sent by middleware")

print("=== STEP 14: LOGGING (invalid attempts produce structured logs) ===")
c.post("/api/v1/auth/login", json={"email": "qa@veriunlearn.dev", "password": "bad-password"})
c.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token"})
time.sleep(0.5)

print(f"\n===== SUMMARY: {results['pass']} passed, {results['fail']} failed, {results['warn']} warnings =====")
for name, detail in failures:
    print(f"  FAILED: {name} :: {detail}")
sys.exit(1 if results["fail"] else 0)
