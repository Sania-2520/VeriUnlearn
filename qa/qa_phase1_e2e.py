"""Full Phase 1 E2E flow against the live PostgreSQL-backed server (port 8001)."""
import csv
import io
import sys

import httpx

BASE = "http://127.0.0.1:8001"
c = httpx.Client(base_url=BASE, timeout=120)
results = {"pass": 0, "fail": 0}
failures = []


def check(name, cond, detail=""):
    if cond:
        results["pass"] += 1
        print(f"  PASS  {name}")
    else:
        results["fail"] += 1
        failures.append((name, detail))
        print(f"  FAIL  {name} -- {detail}")


def make_csv(n=300):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["a", "b", "label"])
    for i in range(n):
        w.writerow([round((i % 7) / 3, 3), round(((i * 2) % 11) / 5, 3), i % 2])
    return buf.getvalue()


# register (fall back to login if already registered)
r = c.post("/api/v1/auth/register", json={"email": "e2e@veriunlearn.dev", "full_name": "E2E User", "password": "password123"})
if r.status_code == 201:
    check("register", True)
    token = r.json()["access_token"]
elif r.status_code == 409:
    check("register (already exists, using login)", True)
    token = c.post("/api/v1/auth/login", json={"email": "e2e@veriunlearn.dev", "password": "password123"}).json()["access_token"]
else:
    check("register", False, r.text[:200])
    sys.exit(1)
h = {"Authorization": f"Bearer {token}"}

# login
r = c.post("/api/v1/auth/login", json={"email": "e2e@veriunlearn.dev", "password": "password123"})
check("login", r.status_code == 200, r.text[:200])

# upload dataset (Postgres FK + JSON columns)
r = c.post("/api/v1/datasets/upload", headers=h, data={"shard_count": "4"}, files={"file": ("synth.csv", make_csv(), "text/csv")})
check("upload dataset", r.status_code == 201, f"{r.status_code}: {r.text[:300]}")
dataset_id = r.json().get("id")

# train model
r = c.post(f"/api/v1/models/train?dataset_id={dataset_id}", headers=h)
check("train model", r.status_code == 201, f"{r.status_code}: {r.text[:300]}")
model_id = r.json().get("id")
check("model ready", r.json().get("status") == "ready", r.text[:200])

# predict
r = c.post(f"/api/v1/models/{model_id}/predict", headers=h, json={"features": {"a": 1.0, "b": -1.0}})
check("predict", r.status_code == 200, r.text[:200])

# privacy search
r = c.post("/api/v1/privacy/search?query=a", headers=h)
check("privacy search", r.status_code == 200, r.text[:200])
target = r.json()["matches"][0]["identity_key"]

# selective unlearning
r = c.post("/api/v1/unlearning/selective", headers=h, json={"identity_key": target, "deletion_type": "records", "method": "retrain"})
check("selective unlearning accepted", r.status_code == 202, f"{r.status_code}: {r.text[:300]}")
request_id = r.json().get("id")

# poll until completed (background task on live server)
import time
status, cert_id = None, None
for _ in range(60):
    time.sleep(2)
    r = c.get(f"/api/v1/unlearning/requests/{request_id}", headers=h)
    if r.status_code != 200:
        continue
    j = r.json()
    status = j.get("status")
    cert_id = j.get("certificate_id")
    if status in ("completed", "failed"):
        break
check("unlearning completes", status == "completed", f"status={status} body={r.text[:300]}")
check("certificate issued", bool(cert_id), "no certificate_id")

# certificate + verify
r = c.get(f"/api/v1/certificates/{cert_id}", headers=h)
check("certificate retrievable", r.status_code == 200, r.text[:200])
r = c.post(f"/api/v1/verification/verify/{cert_id}", headers=h)
check("certificate verifies", r.status_code == 200 and r.json().get("verified") is True, f"{r.status_code}: {r.text[:300]}")

# audit trail tamper check
r = c.get("/api/v1/audit/verify", headers=h)
check("audit chain verified", r.status_code == 200 and r.json().get("verified") is True, f"{r.status_code}: {r.text[:300]}")

# compliance overview
r = c.get("/api/v1/compliance/overview", headers=h)
check("compliance overview", r.status_code == 200, f"{r.status_code}")

# Data persisted in Postgres?
import asyncio
async def pg_counts():
    import asyncpg
    conn = await asyncpg.connect("postgresql://veriunlearn:veriunlearn@127.0.0.1:5433/veriunlearn")
    rows = dict(await conn.fetchrow(
        "SELECT (SELECT count(*) FROM users) u, (SELECT count(*) FROM datasets) d, "
        "(SELECT count(*) FROM dataset_records) r, (SELECT count(*) FROM ml_models) m, "
        "(SELECT count(*) FROM deletion_requests) dr, (SELECT count(*) FROM certificates) ce, "
        "(SELECT count(*) FROM audit_events) ae"))
    await conn.close()
    return rows

counts = asyncio.run(pg_counts())
print(f"  INFO  Postgres rows -> {counts}")
check("users persisted in PG", counts["u"] >= 1)
check("datasets persisted in PG", counts["d"] >= 1)
check("records persisted in PG", counts["r"] >= 1)
check("models persisted in PG", counts["m"] >= 1)
check("deletion_requests persisted in PG", counts["dr"] >= 1)
check("certificates persisted in PG", counts["ce"] >= 1)
check("audit_events persisted in PG", counts["ae"] >= 1)

print(f"\n===== E2E on PostgreSQL: {results['pass']} passed, {results['fail']} failed =====")
for n, d in failures:
    print(f"  FAILED: {n} :: {d}")
sys.exit(1 if results["fail"] else 0)
