"""RBAC matrix validation: admin / auditor / operator / viewer against protected routes."""
import httpx
import sys

BASE = "http://127.0.0.1:8001"
c = httpx.Client(base_url=BASE, timeout=30)
results = {"pass": 0, "fail": 0}
failures = []

USERS = {
    "admin": ("admin@veriunlearn.dev", "admin12345"),
    "auditor": ("auditor@veriunlearn.dev", "auditor123"),
    "operator": ("e2e@veriunlearn.dev", "password123"),
    "viewer": ("viewer@veriunlearn.dev", "viewer12345"),
}

def check(name, cond, detail=""):
    if cond:
        results["pass"] += 1
        print(f"  PASS  {name}")
    else:
        results["fail"] += 1
        failures.append((name, detail))
        print(f"  FAIL  {name} -- {detail}")

# Routes -> expected status per role
CASES = [
    # (route, method, role, expected_status, json_body or None)
    ("/api/v1/admin/users", "GET", "admin", 200, None),
    ("/api/v1/admin/users", "GET", "operator", 403, None),
    ("/api/v1/admin/users", "GET", "viewer", 403, None),
    ("/api/v1/admin/roles", "GET", "admin", 200, None),
    ("/api/v1/admin/roles", "GET", "auditor", 403, None),
    ("/api/v1/admin/overview", "GET", "admin", 200, None),
    ("/api/v1/compliance/report", "POST", "admin", 200, None),
    ("/api/v1/compliance/report", "POST", "viewer", 403, None),
    ("/api/v1/compliance/report", "POST", "operator", 403, None),
    ("/api/v1/compliance/overview", "GET", "viewer", 200, None),
    ("/api/v1/compliance/overview", "GET", "operator", 200, None),
    ("/api/v1/monitoring/system", "GET", "admin", 200, None),
    ("/api/v1/monitoring/system", "GET", "viewer", 403, None),  # matrix: viewer has NO monitoring:read
    ("/api/v1/api-keys", "POST", "admin", 200, {"name": "test-key"}),
    ("/api/v1/api-keys", "POST", "viewer", 403, {"name": "test-key"}),
]

tokens = {}
for role, (email, pwd) in USERS.items():
    r = c.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    tokens[role] = r.json().get("access_token", "") if r.status_code == 200 else ""
    check(f"login {role}", r.status_code == 200, f"{r.status_code} {r.text[:120]}")

for route, method, role, expected, body in CASES:
    token = tokens.get(role, "")
    h = {"Authorization": f"Bearer {token}"}
    if method == "GET":
        r = c.get(route, headers=h)
    else:
        r = c.post(route, headers=h, json=body)
    status_ok = r.status_code == expected
    # treat 200/201 as equivalent
    if expected == 200:
        status_ok = r.status_code in (200, 201)
    label = "as-expected" if status_ok else f"expected {expected}"
    check(f"{method} {route} [{role}] -> {r.status_code} ({label})", status_ok, r.text[:120])

print(f"\n===== RBAC: {results['pass']} passed, {results['fail']} failed =====")
for n, d in failures:
    print(f"  FAILED: {n} :: {d}")
sys.exit(1 if results["fail"] else 0)
