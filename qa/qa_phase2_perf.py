"""Phase 2 Step 19 — Performance: upload, parse, embedding, DB insert, search, delete."""
import statistics
import sys
import time

import psutil
import qa_phase2_common as c

client = c.make_client()
headers = c.auth_headers(client)

print("=== STEP 19: PERFORMANCE ===")


def timed(label, fn):
    t0 = time.perf_counter()
    r = fn()
    dt = (time.perf_counter() - t0) * 1000
    ok = "OK " if r.status_code < 400 else "ERR"
    print(f"  {label:42s} {ok} {dt:8.1f} ms  (status {r.status_code})")
    return r, dt


# small file upload latency
_, small_t = timed("upload 5-row CSV", lambda: c.upload(client, headers, "perf_small.csv", c.csv_bytes(5)))
# medium file (500 rows)
_, med_t = timed("upload 500-row CSV", lambda: c.upload(client, headers, "perf_med.csv", c.csv_bytes(500)))
# large file (5000 rows) -> parse + embed + insert
r_large, large_t = timed("upload 5,000-row CSV (parse+embed+insert)", lambda: c.upload(client, headers, "perf_large.csv", c.csv_bytes(5000)))
# text file (2000 lines)
r_txt, txt_t = timed("upload 2,000-line TXT (parse+insert)", lambda: c.upload(client, headers, "perf_text.txt", c.txt_bytes(2000)))
# PDF (50 pages)
import qa_phase2_common as _c
pdf50 = None
r_pdf, pdf_t = timed("upload 50-page PDF", lambda: c.upload(client, headers, "perf_doc.pdf", _c.pdf_bytes(50)))

# list + detail latency
t0 = time.perf_counter()
for _ in range(10):
    client.get("/api/v1/datasets", headers=headers)
list_ms = (time.perf_counter() - t0) / 10 * 1000
print(f"  {'list /datasets avg (10x)':42s} OK  {list_ms:8.1f} ms")

if r_large.status_code == 201:
    did = r_large.json()["id"]
    t0 = time.perf_counter()
    for _ in range(10):
        client.get(f"/api/v1/datasets/{did}", headers=headers)
    det_ms = (time.perf_counter() - t0) / 10 * 1000
    print(f"  {'GET /datasets/{id} avg (10x)':42s} OK  {det_ms:8.1f} ms")

    # delete latency (with trained model to exercise full cleanup)
    client.post(f"/api/v1/models/train?dataset_id={did}", headers=headers)
    t0 = time.perf_counter()
    r = client.delete(f"/api/v1/datasets/{did}", headers=headers)
    del_ms = (time.perf_counter() - t0) * 1000
    print(f"  {'DELETE dataset (records+vectors+models)':42s} OK  {del_ms:8.1f} ms  (status {r.status_code})")

# memory + cpu of backend process
for proc in psutil.process_iter(["pid", "name", "cmdline"]):
    try:
        cmd = " ".join(proc.info["cmdline"] or [])
        if "uvicorn" in cmd and "8000" in cmd:
            print(f"  {'backend RSS':42s}     {proc.memory_info().rss/1024/1024:8.1f} MB")
            print(f"  {'backend CPU% (0.5s)':42s}     {proc.cpu_percent(interval=0.5):8.1f} %")
            break
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

print(f"\n  upload timings: small={small_t:.0f}ms  med={med_t:.0f}ms  large5k={large_t:.0f}ms  txt2k={txt_t:.0f}ms  pdf50={pdf_t:.0f}ms")
