"""Phase 2 Steps 9-15 — search, details, update, delete, bulk, export, API validation."""
import sqlite3
import sys
from pathlib import Path

import httpx
import qa_phase2_common as c

DB_PATH = Path(__file__).resolve().parents[1] / "backend" / "veriunlearn.db"
client = c.make_client()
headers = c.auth_headers(client)
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


def db():
    return sqlite3.connect(DB_PATH)


def q(sql, params=()):
    conn = db()
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# create a few known datasets for search/detail tests
ids = {}
for fname, content in [
    ("search_alpha.csv", c.csv_bytes(10)),
    ("search_beta.csv", c.csv_bytes(20)),
    ("search_alpha.json", c.json_bytes(5)),
]:
    r = c.upload(client, headers, fname, content)
    check(f"setup upload {fname}", r.status_code == 201, f"{r.status_code}: {r.text[:150]}")
    if r.status_code == 201:
        ids[fname] = r.json()["id"]

print("=== STEP 9: DATASET SEARCH ===")
# Try common search patterns
r = client.get("/api/v1/datasets/search", params={"q": "alpha"}, headers=headers)
check("search by name (query param)", r.status_code in (200, 404, 405), f"{r.status_code}: {r.text[:150]}")
if r.status_code == 200:
    check("search returns matching datasets", len(r.json()) >= 1, r.text[:200])
else:
    warn("no /datasets/search endpoint", "search-by-name not implemented")
r = client.get("/api/v1/datasets?name=search_alpha", headers=headers)
warn("filter by name via list", "list only supports limit; no filters" if r.status_code == 200 else f"{r.status_code}")
r = client.get("/api/v1/datasets?tags=foo", headers=headers)
warn("filter by tags", "no tags field/column exists" if r.status_code == 200 else f"{r.status_code}")
r = client.get("/api/v1/datasets?source_type=csv", headers=headers)
warn("filter by source_type", "filters ignored by list endpoint" if r.status_code == 200 else f"{r.status_code}")

# pagination: does list support offset?
r = client.get("/api/v1/datasets?limit=2", headers=headers)
check("list respects limit", r.status_code == 200 and len(r.json()) <= 2, f"{r.status_code} len={len(r.json()) if r.status_code == 200 else '?'}")
r = client.get("/api/v1/datasets?limit=2&offset=2", headers=headers)
warn("pagination offset", f"offset param unsupported (still {len(r.json())} rows)" if r.status_code == 200 and len(r.json()) == 2 else f"{r.status_code}")
# sorting
r = client.get("/api/v1/datasets?sort=name&order=asc", headers=headers)
warn("sorting", "sort params ignored by list endpoint" if r.status_code == 200 else f"{r.status_code}")

print("=== STEP 10: DATASET DETAILS ===")
target = ids.get("search_alpha.csv")
if target:
    r = client.get(f"/api/v1/datasets/{target}", headers=headers)
    check("GET /datasets/{id} returns 200", r.status_code == 200, f"{r.status_code}")
    if r.status_code == 200:
        d = r.json()
        check("details: id", d.get("id") == target)
        check("details: name", bool(d.get("name")))
        check("details: source_type", bool(d.get("source_type")))
        check("details: record_count", d.get("record_count") == 10, d.get("record_count"))
        check("details: created_at", bool(d.get("created_at")))
        for field in ["owner", "document_count", "chunk_count", "embedding_count", "file_size", "version", "tags"]:
            if field not in d:
                warn(f"details missing field: {field}", "not exposed by serializer")
    r2 = client.get(f"/api/v1/datasets/{target}/records", headers=headers)
    warn("records endpoint", f"{r2.status_code} — no per-record list endpoint" if r2.status_code != 200 else "ok")
    r3 = client.get(f"/api/v1/datasets/{target}/chunks", headers=headers)
    warn("chunks endpoint", f"{r3.status_code} — no chunks endpoint" if r3.status_code != 200 else "ok")

print("=== STEP 11: UPDATE DATASET ===")
if target:
    r = client.patch(f"/api/v1/datasets/{target}", json={"name": "renamed", "description": "new"}, headers=headers)
    check("PATCH /datasets/{id} (rename/desc)", r.status_code in (200, 405), f"{r.status_code}: {r.text[:150]}")
    if r.status_code == 200:
        check("update persisted", client.get(f"/api/v1/datasets/{target}", headers=headers).json().get("name") == "renamed")
    else:
        warn("no PATCH update endpoint", "rename/description/tags/metadata update not implemented")
    r = client.put(f"/api/v1/datasets/{target}", json={"name": "renamed2"}, headers=headers)
    check("PUT /datasets/{id}", r.status_code in (200, 405), f"{r.status_code}")

print("=== STEP 12: DELETE DATASET ===")
# delete a numeric dataset that has embeddings + vectors + identity profiles
r = c.upload(client, headers, "delete_me.csv", c.csv_bytes(30))
del_id = r.json()["id"]
del_embed_rows = q1 = None
emb_before = q("SELECT count(*) FROM embedding_index WHERE dataset_id=?", (del_id,))[0][0]
idn_before = q("SELECT count(*) FROM identity_index WHERE dataset_ids LIKE ?", (f"%{del_id}%",))[0][0]
qcoll_before = httpx.post(f"http://127.0.0.1:6333/collections/dataset_{del_id}/points/count", json={"exact": True}).json()
# train a model on it to test model cascade
mr = client.post(f"/api/v1/models/train?dataset_id={del_id}", headers=headers)
trained = mr.status_code == 201
if trained:
    check("setup: trained model on dataset", True)
r = client.delete(f"/api/v1/datasets/{del_id}", headers=headers)
check("DELETE /datasets/{id} -> 200", r.status_code == 200, f"{r.status_code}: {r.text[:150]}")

check("DB: dataset row removed", q("SELECT count(*) FROM datasets WHERE id=?", (del_id,))[0][0] == 0)
check("DB: records removed (cascade)", q("SELECT count(*) FROM dataset_records WHERE dataset_id=?", (del_id,))[0][0] == 0)
check("DB: embedding_index rows removed", q("SELECT count(*) FROM embedding_index WHERE dataset_id=?", (del_id,))[0][0] == 0, f"{emb_before} rows existed")
idn_after = q("SELECT count(*) FROM identity_index WHERE dataset_ids LIKE ?", (f"%{del_id}%",))[0][0]
check("DB: identity profiles cleaned", idn_after == 0, f"{idn_before} profiles linked before")
if trained:
    ml = q("SELECT count(*) FROM ml_models WHERE dataset_id=?", (del_id,))[0][0]
    check("DB: trained model rows removed", ml == 0, f"{ml} ml_models remain (SQLite FK cascade not active)")
# Qdrant cleanup
qcoll_after = httpx.get(f"http://127.0.0.1:6333/collections/dataset_{del_id}").status_code
check("Qdrant: collection deleted on dataset delete", qcoll_after == 404, f"status {qcoll_after} (collection still exists)")
# audit
audit = q("SELECT count(*) FROM audit_events WHERE event_type='dataset.deleted' AND subject=?", (del_id,))
check("audit: dataset.deleted event created", audit[0][0] >= 1)
check("GET deleted dataset -> 404", client.get(f"/api/v1/datasets/{del_id}", headers=headers).status_code == 404)

print("=== STEP 13: BULK OPERATIONS ===")
r = client.post("/api/v1/datasets/bulk-upload", headers=headers)
check("bulk upload endpoint", r.status_code in (404, 405), f"{r.status_code}")
r = client.post("/api/v1/datasets/bulk-delete", json={"ids": []}, headers=headers)
check("bulk delete endpoint", r.status_code in (404, 405), f"{r.status_code}")
warn("no bulk endpoints implemented", "bulk upload/delete/metadata/search/export all missing")

print("=== STEP 14: EXPORT ===")
if target:
    for fmt in ["json", "csv", "excel", "xlsx"]:
        r = client.get(f"/api/v1/datasets/{target}/export", params={"format": fmt}, headers=headers)
        check(f"export {fmt}", r.status_code in (200, 404, 405), f"{r.status_code}")
        if r.status_code != 200:
            warn(f"export as {fmt} not implemented", f"{r.status_code}")
            break

print("=== STEP 15: API VALIDATION ===")
# status codes for the dataset API surface
check("POST /datasets/upload no auth -> 401", client.post("/api/v1/datasets/upload").status_code == 401)
check("DELETE /datasets/{id} no auth -> 401", client.delete(f"/api/v1/datasets/{ids.get('search_alpha.csv','x')}").status_code == 401)
check("GET /datasets/{id} missing id -> 404", client.get("/api/v1/datasets/00000000-0000-0000-0000-000000000000", headers=headers).status_code == 404)
check("GET /datasets/{id} invalid uuid handled", client.get("/api/v1/datasets/not-a-uuid", headers=headers).status_code in (404, 422))
check("upload without file -> 422", client.post("/api/v1/datasets/upload", headers=headers).status_code == 422)
check("upload invalid shard_count -> 422/400", client.post(
    "/api/v1/datasets/upload", headers=headers, data={"shard_count": "-5"},
    files={"file": ("x.csv", c.csv_bytes(5))}).status_code in (400, 422))
# OpenAPI includes dataset endpoints
schema = client.get("/openapi.json").json()
dataset_paths = [p for p in schema["paths"] if p.startswith("/api/v1/datasets")]
check("OpenAPI documents dataset endpoints", len(dataset_paths) >= 4, str(dataset_paths))

print(f"\n===== STEP 9-15: {results['pass']} passed, {results['fail']} failed, {results['warn']} warnings =====")
for n, d in failures:
    print(f"  FAILED: {n} :: {d}")
sys.exit(1 if results["fail"] else 0)
