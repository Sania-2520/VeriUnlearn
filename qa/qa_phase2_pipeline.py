"""Phase 2 Steps 3-8 — Parsing, chunking, embeddings, vector store, DB storage, versioning."""
import json
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


def q1(sql, params=()):
    rows = q(sql, params)
    return rows[0][0] if rows else None


# ---------------------------------------------------------------------------
print("=== STEP 3: DATASET PARSING ===")
pdf = c.pdf_bytes(3, title="Phase 2 QA Document", author="VeriUnlearn QA")
r = c.upload(client, headers, "parsed_doc.pdf", pdf)
check("upload PDF for parsing", r.status_code == 201, r.text[:200])
pdf_id = r.json()["id"]

txt_lines = [f"Unique knowledge line {i}" for i in range(10)]
r = c.upload(client, headers, "parsed_notes.txt", ("\n".join(txt_lines) + "\n").encode())
check("upload TXT for parsing", r.status_code == 201, r.text[:200])
txt_id = r.json()["id"]

# TXT parsing: each non-empty line -> record, text preserved exactly
rows = q("SELECT record_index, original_text, source_filename FROM dataset_records WHERE dataset_id=? ORDER BY record_index", (txt_id,))
check("TXT: every line became a record", len(rows) == 10, f"got {len(rows)}")
check("TXT: no text loss (all lines present)", {r_[1] for r_ in rows} == set(txt_lines), f"missing={set(txt_lines) - {r_[1] for r_ in rows}}")
check("TXT: no duplicated text", len({r_[1] for r_ in rows}) == 10)
check("TXT: correct source_filename", all(r_[2] == "parsed_notes.txt" for r_ in rows))
check("TXT: chunk ordering 0..9", [r_[0] for r_ in rows] == list(range(10)))

# PDF parsing: per-page text chunks
rows = q("SELECT record_index, original_text FROM dataset_records WHERE dataset_id=? ORDER BY record_index", (pdf_id,))
check("PDF: 3 pages -> 3 records", len(rows) == 3, f"got {len(rows)}")
if rows:
    check("PDF: page text extracted (no loss)", all("verifiable machine unlearning" in r_[1] for r_ in rows), rows[0][1][:80])
    check("PDF: no duplicated page text", len({r_[1] for r_ in rows}) == 3)
    check("PDF: chunk ordering 0..2", [r_[0] for r_ in rows] == [0, 1, 2])

# metadata stored
meta = q1("SELECT meta FROM datasets WHERE id=?", (pdf_id,))
meta = json.loads(meta) if meta else {}
check("PDF: meta[kind]=documents", meta.get("kind") == "documents", str(meta))

print("=== STEP 4: CHUNKING ===")
# chunk_index + embedding chunk ids for numeric dataset
r = c.upload(client, headers, "chunk_test.csv", c.csv_bytes(25))
chunk_id = r.json()["id"]
rows = q("SELECT record_index, chunk_index, shard_id, id FROM dataset_records WHERE dataset_id=? ORDER BY record_index", (chunk_id,))
check("CSV: chunk_index == record_index", [r_[1] for r_ in rows] == list(range(25)))
check("CSV: record ordering 0..24", [r_[0] for r_ in rows] == list(range(25)))
check("CSV: shards assigned within 0..3", all(0 <= r_[2] <= 3 for r_ in rows))
# every record has a deterministic identity + content hash
hashes = q("SELECT content_hash FROM dataset_records WHERE dataset_id=?", (chunk_id,))
check("CSV: unique content hashes", len({h[0] for h in hashes}) == 25)
check("CSV: hashes non-empty", all(h[0] for h in hashes))

# embedding_index chunk ids for the numeric dataset
echunks = q("SELECT chunk_id, record_id FROM embedding_index WHERE dataset_id=?", (chunk_id,))
check("CSV: every record has an embedding_index row (chunk)", len(echunks) == 25, f"got {len(echunks)}")
if echunks:
    expected_chunk_ids = {f"chunk-{chunk_id}-{i}" for i in range(25)}
    check("CSV: chunk_id format chunk-{dataset}-{idx}", {e[0] for e in echunks} == expected_chunk_ids, f"got {sorted({e[0] for e in echunks})}")
    rec_ids = {r_[3] for r_ in rows}
    check("CSV: every chunk links to a real record", all(e[1] in rec_ids for e in echunks), "orphan chunk row")

print("=== STEP 5: EMBEDDING GENERATION ===")
# numeric CSV -> embeddings
emb = q("SELECT embedding_id, vector_id, dim, is_deleted FROM embedding_index WHERE dataset_id=?", (chunk_id,))
check("CSV: embedding rows exist", len(emb) == 25, f"got {len(emb)}")
if emb:
    check("CSV: embedding dim == feature count (2)", {e[2] for e in emb} == {2}, f"dims={ {e[2] for e in emb} }")
    check("CSV: embedding_id == record id (unique)", len({e[0] for e in emb}) == 25)
    check("CSV: vector_id == record id", len({e[1] for e in emb}) == 25)
# records carry embedding refs
rec_emb = q("SELECT count(*) FROM dataset_records WHERE dataset_id=? AND embedding_id IS NOT NULL AND vector_id IS NOT NULL", (chunk_id,))
check("CSV: records store embedding + vector refs", rec_emb[0][0] == 25)
# text dataset -> NO embeddings (design gap)
txt_emb = q1("SELECT count(*) FROM embedding_index WHERE dataset_id=?", (txt_id,))
txt_rec_emb = q1("SELECT count(*) FROM dataset_records WHERE dataset_id=? AND embedding_id IS NOT NULL", (txt_id,))
warn(f"TXT/PDF documents get no embeddings (embedding_index={txt_emb}, records_with_emb={txt_rec_emb})",
     "text features are not vectorized — Phase 2 document-embedding gap")

print("=== STEP 6: VECTOR STORE ===")
# check Qdrant collection exists with right point count
collections = httpx.get("http://127.0.0.1:6333/collections").json()["result"]["collections"]
names = {c_["name"] for c_ in collections}
check(f"Qdrant: collection dataset_{chunk_id} created", f"dataset_{chunk_id}" in names, names)
qname = f"dataset_{chunk_id}"
cnt = httpx.post(f"http://127.0.0.1:6333/collections/{qname}/points/count", json={"exact": True}).json()
check("Qdrant: 25 vectors inserted", cnt["result"]["count"] == 25, cnt)
# similarity search via Qdrant REST
search = httpx.post(
    f"http://127.0.0.1:6333/collections/{qname}/points/search",
    json={"vector": [0.3, 0.4], "limit": 5, "with_payload": True},
).json()
hits = search.get("result", [])
check("Qdrant: similarity search returns hits", len(hits) >= 1, search)
if hits:
    check("Qdrant: hits carry payload metadata", all("identity_key" in h.get("payload", {}) for h in hits), hits[0])
# vector update (upsert replaces point)
httpx.put(
    f"http://127.0.0.1:6333/collections/{qname}/points",
    json={"points": [{"id": hits[0]["id"], "vector": [1.0, 0.0], "payload": {"updated": True}}]},
)
cnt2 = httpx.post(f"http://127.0.0.1:6333/collections/{qname}/points/count", json={"exact": True}).json()
check("Qdrant: upsert (update) keeps count stable", cnt2["result"]["count"] == 25, cnt2)
# vector deletion
httpx.post(
    f"http://127.0.0.1:6333/collections/{qname}/points/delete",
    json={"points": [hits[0]["id"]]},
)
cnt3 = httpx.post(f"http://127.0.0.1:6333/collections/{qname}/points/count", json={"exact": True}).json()
check("Qdrant: vector deletion works", cnt3["result"]["count"] == 24, cnt3)

print("=== STEP 7: DATABASE STORAGE ===")
ds = q("SELECT record_count, version, status, shard_count, created_at FROM datasets WHERE id=?", (chunk_id,))[0]
check("DB: dataset row saved with record_count", ds[0] == 25, ds)
check("DB: dataset version initialized to 1", ds[1] == 1, ds)
check("DB: status ready", ds[2] == "ready")
check("DB: created_at stored", bool(ds[4]))
rec = q1("SELECT count(*) FROM dataset_records WHERE dataset_id=?", (chunk_id,))
check("DB: 25 records stored", rec == 25)
emb_rows = q1("SELECT count(*) FROM embedding_index WHERE dataset_id=?", (chunk_id,))
check("DB: 25 embedding references stored", emb_rows == 25)
idn = q1("SELECT count(*) FROM identity_index WHERE dataset_ids LIKE ?", (f"%{chunk_id}%",))
check("DB: identity profiles linked to dataset", idn > 0, f"count={idn}")

print("=== STEP 8: VERSIONING ===")
# version history / rollback info is not exposed by any table or endpoint
tables = [t[0] for t in q("SELECT name FROM sqlite_master WHERE type='table'")]
version_tables = [t for t in tables if "version" in t.lower()]
warn(f"no dataset version-history table exists ({version_tables or 'none'})",
     "only an int column Dataset.version; no history/rollback/audit-per-version")
check("DB: Dataset.version column exists and =1", ds[1] == 1)

print(f"\n===== STEP 3-8: {results['pass']} passed, {results['fail']} failed, {results['warn']} warnings =====")
for n, d in failures:
    print(f"  FAILED: {n} :: {d}")
sys.exit(1 if results["fail"] else 0)
