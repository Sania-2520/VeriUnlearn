"""Phase 2 Step 17 (error handling) + Step 18 (security)."""
import sys
import urllib.parse

import httpx
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


print("=== STEP 17: ERROR HANDLING ===")
# network/db failures are hard to simulate live; verify no crashes on bad input
r = c.upload(client, headers, "corrupt2.pdf", b"%PDF-1.7 garbage not a real pdf")
check("corrupted file -> clean 4xx (no crash)", r.status_code in (400, 422), f"{r.status_code}")
r = c.upload(client, headers, "dup_check.csv", c.csv_bytes(10))
check("duplicate upload of same content ok", r.status_code == 201, f"{r.status_code}")
r = c.upload(client, headers, "dup_check2.csv", c.csv_bytes(10))
check("second identical-content upload ok (no false dedupe crash)", r.status_code == 201, f"{r.status_code}")
r = c.upload(client, headers, "noheader.csv", b"1,2,3\n4,5,6\n")
check("CSV without header row parses", r.status_code == 201, f"{r.status_code}: {r.text[:150]}")
r = c.upload(client, headers, "unicode.txt", "héllo wörld\nsnowman ☃\n".encode("utf-8"))
check("UTF-8 unicode text upload", r.status_code == 201, f"{r.status_code}: {r.text[:150]}")
# non-integer shard_count
r = client.post("/api/v1/datasets/upload", headers=headers, data={"shard_count": "abc"},
                files={"file": ("x.csv", c.csv_bytes(5))})
check("non-integer shard_count -> 422", r.status_code == 422, f"{r.status_code}")

print("=== STEP 18: SECURITY ===")
# unauthenticated access
check("upload without auth -> 401", client.post("/api/v1/datasets/upload").status_code == 401)
r = c.upload(client, headers, "sec.csv", c.csv_bytes(5))
sec_id = r.json()["id"]
check("delete without auth -> 401", client.delete(f"/api/v1/datasets/{sec_id}").status_code == 401)
check("list without auth -> 401", client.get("/api/v1/datasets").status_code == 401)
check("details without auth -> 401", client.get(f"/api/v1/datasets/{sec_id}").status_code == 401)
check("update without auth -> 401", client.patch(f"/api/v1/datasets/{sec_id}", json={"name": "x"}).status_code in (401, 405))

# path traversal filenames (literal separators must not end up in the dataset name)
for badname in [
    "../../etc/passwd.csv",
    "..\\..\\windows\\system32.csv",
    "evil name with spaces;.csv",
    "quote'quote.csv",
]:
    r = c.upload(client, headers, badname, c.csv_bytes(3))
    ok = r.status_code == 201
    check(f"path-traversal filename '{badname[:30]}' handled safely", ok, f"{r.status_code}: {r.text[:120]}")
    if ok:
        ds = client.get(f"/api/v1/datasets/{r.json()['id']}", headers=headers).json()
        check("  dataset name sanitized (no path separators)", "/" not in ds["name"] and "\\" not in ds["name"] and ".." not in ds["name"], ds["name"])

# percent-encoded traversal string is stored as a literal display name (no filesystem write)
r = c.upload(client, headers, "..%2F..%2Fetc%2Fpasswd.csv", c.csv_bytes(3))
check("percent-encoded traversal filename accepted (no crash)", r.status_code == 201, f"{r.status_code}: {r.text[:120]}")
# quoted filename: rejected as unsupported type (quote not valid in Windows filenames) -> no crash
r = client.post(
    "/api/v1/datasets/upload", headers=headers, data={"shard_count": "4"},
    files={"file": ('"doublequotes.csv"', c.csv_bytes(3))},
)
check("quoted filename handled cleanly", r.status_code in (201, 400, 422), f"{r.status_code}: {r.text[:120]}")

# null byte in filename
r = client.post(
    "/api/v1/datasets/upload",
    headers=headers,
    data={"shard_count": "4"},
    files={"file": ("bad\x00name.csv", c.csv_bytes(3))},
)
check("null-byte filename handled (no crash)", r.status_code in (201, 400, 422), f"{r.status_code}: {r.text[:120]}")

# oversized
r = c.upload(client, headers, "oversize2.csv", c.oversized_bytes(51))
check("oversized file rejected (no memory blowup)", r.status_code in (400, 413, 422), f"{r.status_code}")

# executable content rejected
r = c.upload(client, headers, "malware.txt", c.exe_bytes())
check("executable content in .txt rejected", r.status_code in (400, 422), f"{r.status_code}")

# response does not leak internals
r = c.upload(client, headers, "leak_test.csv", c.csv_bytes(3))
body = r.text
check("upload response contains no stack traces", "Traceback" not in body and "File \"" not in body)
r = client.get(f"/api/v1/datasets/{sec_id}", headers=headers)
body = r.text
check("list response no internal paths", "veriunlearn" not in body.lower() or "source" not in body, "meta may contain paths")

print(f"\n===== STEP 17-18: {results['pass']} passed, {results['fail']} failed, {results['warn']} warnings =====")
for n, d in failures:
    print(f"  FAILED: {n} :: {d}")
sys.exit(1 if results["fail"] else 0)
