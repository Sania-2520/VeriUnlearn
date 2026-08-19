"""Phase 2 Step 20 — End-to-end dataset lifecycle flow."""
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


print("=== STEP 20: END-TO-END DATASET FLOW ===")
# 1. Create dataset
r = c.upload(client, headers, "e2e_master.csv", c.csv_bytes(100))
check("create: upload dataset", r.status_code == 201, f"{r.status_code}: {r.text[:200]}")
did = r.json()["id"]

# 2. Parse documents
conn = sqlite3.connect(DB_PATH)
recs = conn.execute("SELECT count(*) FROM dataset_records WHERE dataset_id=?", (did,)).fetchone()[0]
check("parse: 100 records stored", recs == 100, recs)

# 3. Generate chunks
chunks = conn.execute("SELECT count(*) FROM embedding_index WHERE dataset_id=?", (did,)).fetchone()[0]
check("chunk: 100 embedding_index rows (chunks)", chunks == 100, chunks)

# 4. Generate embeddings
emb = conn.execute("SELECT count(*) FROM dataset_records WHERE dataset_id=? AND embedding_id IS NOT NULL", (did,)).fetchone()[0]
check("embedding: 100 records embedded", emb == 100, emb)
qcoll = httpx.post(f"http://127.0.0.1:6333/collections/dataset_{did}/points/count", json={"exact": True}).json()
check("embedding: 100 vectors in Qdrant", qcoll["result"]["count"] == 100, qcoll)
conn.close()

# 5. Store dataset
d = client.get(f"/api/v1/datasets/{did}", headers=headers).json()
check("store: dataset retrievable", d.get("id") == did)
check("store: version=1", d.get("version", 1) == 1)

# 6. Search dataset (list + detail; search-by-name missing)
lst = client.get("/api/v1/datasets", headers=headers).json()
check("search: dataset present in list", any(x["id"] == did for x in lst))

# 7. View details
check("details: name/source/records present", d.get("name") == "e2e_master" and d.get("record_count") == 100)

# 8. Update metadata (no endpoint -> WARN)
r = client.patch(f"/api/v1/datasets/{did}", json={"description": "E2E test dataset"}, headers=headers)
warn("update: PATCH not implemented", "rename/description update unavailable (feature gap)" if r.status_code != 200 else "ok")

# 9. Export (no endpoint -> WARN)
r = client.get(f"/api/v1/datasets/{did}/export?format=csv", headers=headers)
warn("export: not implemented", "no dataset export endpoint (feature gap)" if r.status_code != 200 else "ok")

# 10. Train on it (proves the dataset is usable downstream)
r = client.post(f"/api/v1/models/train?dataset_id={did}", headers=headers)
check("train: model trains on dataset", r.status_code == 201 and r.json().get("status") == "ready", f"{r.status_code}: {r.text[:200]}")

# 11. Delete dataset
r = client.delete(f"/api/v1/datasets/{did}", headers=headers)
check("delete: DELETE succeeds", r.status_code == 200, f"{r.status_code}: {r.text[:200]}")

# 12. Verify complete cleanup
conn = sqlite3.connect(DB_PATH)
checks = {
    "cleanup: dataset row gone": conn.execute("SELECT count(*) FROM datasets WHERE id=?", (did,)).fetchone()[0] == 0,
    "cleanup: records gone": conn.execute("SELECT count(*) FROM dataset_records WHERE dataset_id=?", (did,)).fetchone()[0] == 0,
    "cleanup: chunks/embedding rows gone": conn.execute("SELECT count(*) FROM embedding_index WHERE dataset_id=?", (did,)).fetchone()[0] == 0,
    "cleanup: model rows gone": conn.execute("SELECT count(*) FROM ml_models WHERE dataset_id=?", (did,)).fetchone()[0] == 0,
    "cleanup: model_shards gone": conn.execute(
        "SELECT count(*) FROM model_shards WHERE model_id NOT IN (SELECT id FROM ml_models)").fetchone()[0] == 0,
}
conn.close()
for name, ok in checks.items():
    check(name, ok)
qcoll_after = httpx.get(f"http://127.0.0.1:6333/collections/dataset_{did}").status_code
check("cleanup: Qdrant collection deleted", qcoll_after == 404, qcoll_after)
check("cleanup: no orphan embedding_index rows (all reference live datasets)",
      sqlite3.connect(DB_PATH).execute(
          "SELECT count(*) FROM embedding_index WHERE dataset_id NOT IN (SELECT id FROM datasets)").fetchone()[0] == 0)

print(f"\n===== STEP 20: {results['pass']} passed, {results['fail']} failed, {results['warn']} warnings =====")
for n, d in failures:
    print(f"  FAILED: {n} :: {d}")
sys.exit(1 if results["fail"] else 0)
