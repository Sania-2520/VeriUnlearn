"""Verify Qdrant vector operations + backend monitoring/Redis integration."""
import httpx

c = httpx.Client(base_url="http://127.0.0.1:8001", timeout=30)
r = c.post("/api/v1/auth/login", json={"email": "e2e@veriunlearn.dev", "password": "password123"})
token = r.json()["access_token"]
h = {"Authorization": f"Bearer {token}"}

# Qdrant REST directly
q = httpx.Client(base_url="http://127.0.0.1:6333", timeout=30)
collections = q.get("/collections").json()["result"]["collections"]
print(f"Qdrant collections: {[col['name'] for col in collections]}")
for col in collections:
    name = col["name"]
    info = q.get(f"/collections/{name}").json()["result"]
    print(f"  {name}: points_count={info.get('points_count')} status={info.get('status')}")

# Vector search on the active collection
if collections:
    name = collections[0]["name"]
    # check collection points count via scroll (count endpoint)
    cnt = q.post(f"/collections/{name}/points/count", json={"exact": True}).json()
    print(f"  count endpoint -> {cnt['result']['count']} points")
    search = q.post(
        f"/collections/{name}/points/search",
        json={"vector": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6], "limit": 3},
    ).json()
    hits = search.get("result", [])
    print(f"  search hits: {len(hits)} (first id: {hits[0]['id'] if hits else 'n/a'})")

# Monitoring snapshot from backend (dependencies: DB/Redis/Qdrant/vector store)
r = c.get("/api/v1/monitoring/snapshot", headers=h)
snap = r.json()
print(f"monitoring snapshot status={r.status_code}")
deps = snap.get("dependencies", {})
for name, v in deps.items():
    print(f"  dep {name}: healthy={v.get('healthy')} detail={v.get('detail')}")
api = snap.get("api", {})
print(f"  api: latency={api.get('avg_latency_ms')}ms error_rate={api.get('error_rate')} uptime={api.get('uptime_seconds')}s")
