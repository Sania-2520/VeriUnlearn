"""Phase 1 performance measurement: latency, startup, memory."""
import time
import statistics
import sys

import httpx

BASE = "http://127.0.0.1:8000"
c = httpx.Client(base_url=BASE, timeout=30)

# --- login latency (50 attempts) ---
r = c.post("/api/v1/auth/register", json={"email": "perf@veriunlearn.dev", "full_name": "Perf", "password": "password123"})
lat = []
for _ in range(50):
    t0 = time.perf_counter()
    r = c.post("/api/v1/auth/login", json={"email": "perf@veriunlearn.dev", "password": "password123"})
    lat.append((time.perf_counter() - t0) * 1000)
token = r.json()["access_token"]
h = {"Authorization": f"Bearer {token}"}
print(f"login latency   : avg={statistics.mean(lat):.1f}ms  p95={sorted(lat)[int(len(lat)*0.95)]:.1f}ms  min={min(lat):.1f}ms  max={max(lat):.1f}ms")

# --- health latency ---
lat = []
for _ in range(50):
    t0 = time.perf_counter()
    c.get("/health")
    lat.append((time.perf_counter() - t0) * 1000)
print(f"health latency  : avg={statistics.mean(lat):.1f}ms  p95={sorted(lat)[int(len(lat)*0.95)]:.1f}ms  max={max(lat):.1f}ms")

# --- protected API latency ---
lat = []
for _ in range(30):
    t0 = time.perf_counter()
    c.get("/api/v1/auth/me", headers=h)
    lat.append((time.perf_counter() - t0) * 1000)
print(f"/auth/me latency: avg={statistics.mean(lat):.1f}ms  p95={sorted(lat)[int(len(lat)*0.95)]:.1f}ms  max={max(lat):.1f}ms")

# --- concurrent burst (100 parallel health + login) ---
import threading
results = []
def worker():
    t0 = time.perf_counter()
    c.get("/health")
    results.append((time.perf_counter() - t0) * 1000)
threads = [threading.Thread(target=worker) for _ in range(100)]
t0 = time.perf_counter()
for t in threads: t.start()
for t in threads: t.join()
total = time.perf_counter() - t0
print(f"100 parallel /health: total={total:.2f}s  avg={statistics.mean(results):.1f}ms  max={max(results):.1f}ms")

# --- memory of backend process ---
import psutil
for proc in psutil.process_iter(["pid", "name", "cmdline"]):
    try:
        cmd = " ".join(proc.info["cmdline"] or [])
        if "uvicorn" in cmd and "8000" in cmd:
            print(f"backend RSS      : {proc.memory_info().rss/1024/1024:.1f} MB  (pid {proc.info['pid']})")
            print(f"backend CPU%     : {proc.cpu_percent(interval=0.5):.1f}%")
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
