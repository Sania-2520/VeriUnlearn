"""Phase 2 Steps 1-2 — Upload Validation + File Validation."""
import sys

import qa_phase2_common as c

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


print("=== STEP 1: UPLOAD VALIDATION (format matrix) ===")
cases = [
    ("small.csv", c.csv_bytes(30), "csv", True),
    ("data.csv", c.csv_bytes(400), "csv", True),
    ("records.json", c.json_bytes(20), "json", True),
    ("lines.jsonl", c.jsonl_bytes(20), "jsonl", True),
    ("notes.txt", c.txt_bytes(12), "txt", True),
    ("report.pdf", c.pdf_bytes(3), "pdf", True),
    ("doc.md", c.md_bytes(), "md", False),      # markdown not supported
    ("doc.docx", c.docx_bytes(), "docx", False),  # docx not supported
]
ids = {}
for fname, content, stype, expect_ok in cases:
    r = c.upload(client, headers, fname, content)
    if expect_ok:
        ok = r.status_code == 201
        check(f"upload {fname} ({stype})", ok, f"{r.status_code}: {r.text[:200]}")
        if ok:
            j = r.json()
            ids[stype] = j["id"]
            check(f"  metadata: name='{j['name']}'", j["name"] == fname.rsplit(".", 1)[0], f"name={j['name']}")
            check(f"  metadata: source_type='{j['source_type']}'", j["source_type"] == stype, f"type={j['source_type']}")
            check(f"  metadata: record_count>0", j["record_count"] > 0, f"records={j['record_count']}")
            check(f"  metadata: status='ready'", j["status"] == "ready", j["status"])
            check(f"  metadata: created_at present", bool(j.get("created_at")), j.get("created_at"))
            check(f"  metadata: id is uuid", len(j["id"]) == 36, j["id"])
    else:
        ok = r.status_code in (400, 415, 422)
        check(f"upload {fname} ({stype}) rejected cleanly", ok, f"{r.status_code}: {r.text[:200]}")
        if r.status_code == 201:
            warn(f"  {fname} unexpectedly accepted", "feature may be implemented now")
            ids[stype] = r.json()["id"]

# small file
r = c.upload(client, headers, "tiny.csv", b"a,b,label\n1,2,0\n")
check("tiny 1-record CSV upload", r.status_code == 201, f"{r.status_code}: {r.text[:200]}")

# duplicate upload (same bytes, new name)
first = c.upload(client, headers, "dup_a.csv", c.csv_bytes(50))
second = c.upload(client, headers, "dup_b.csv", c.csv_bytes(50))
check("duplicate content upload #1", first.status_code == 201)
check("duplicate content upload #2", second.status_code == 201)
if first.status_code == 201 and second.status_code == 201:
    check("duplicates stored as separate datasets", first.json()["id"] != second.json()["id"])

print("=== STEP 2: FILE VALIDATION (invalid inputs) ===")
bad_cases = [
    ("corrupt.pdf", c.corrupt_pdf_bytes(), "corrupted PDF"),
    ("empty.pdf", c.empty_pdf_bytes(), "empty PDF"),
    ("virus.exe", c.exe_bytes(), "executable"),
    ("notes.txt", c.exe_bytes(), "executable renamed .txt"),
    ("bad.json", b"{not valid json", "malformed JSON"),
    ("bad.jsonl", b'{"a":1}\nnot-json\n{"a":2}\n', "malformed JSONL"),
    ("protected.pdf", c.encrypted_pdf_bytes(), "password-protected PDF"),
    ("big.csv", c.oversized_bytes(51), "oversized (>50MB)"),
]
for fname, content, label in bad_cases:
    r = c.upload(client, headers, fname, content)
    ok = r.status_code in (400, 413, 415, 422)
    check(f"{label} ({fname}) rejected with 4xx", ok, f"{r.status_code}: {r.text[:200]}")
    if r.status_code == 500:
        check(f"  no 500 for {label}", False, f"500: {r.text[:300]}")
    elif ok:
        body = r.json()
        msg = body.get("detail") or body.get("message") or ""
        check(f"  user-friendly message for {label}", bool(msg) and len(str(msg)) > 5, f"detail={msg}")

# empty file
r = c.upload(client, headers, "empty.csv", b"")
check("empty file rejected", r.status_code in (400, 422), f"{r.status_code}: {r.text[:200]}")

# unknown suffix
r = c.upload(client, headers, "archive.rar", b"RAR data here")
check("unsupported .rar rejected", r.status_code in (400, 415, 422), f"{r.status_code}: {r.text[:200]}")

# file with no extension
r = c.upload(client, headers, "noext", b"some content without extension")
check("extensionless file rejected", r.status_code in (400, 415, 422), f"{r.status_code}: {r.text[:200]}")

print(f"\n===== STEP 1-2: {results['pass']} passed, {results['fail']} failed, {results['warn']} warnings =====")
for n, d in failures:
    print(f"  FAILED: {n} :: {d}")
sys.exit(1 if results["fail"] else 0)
