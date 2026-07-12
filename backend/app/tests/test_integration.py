"""End-to-end integration tests against the live server on port 8000.

Run directly: python test_integration.py
Requires the full stack (docker compose up) running on localhost:8000.
"""

import time
import urllib.request
import urllib.error
import json
import sys

BASE = "http://localhost:8000/api/v1"
HEADERS = {"Content-Type": "application/json"}
PASS = 0
FAIL = 0


def req(method, path, body=None, token=None, expect=200):
    global PASS, FAIL
    url = f"{BASE}{path}"
    h = HEADERS.copy()
    if token:
        h["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body else None
    try:
        r = urllib.request.Request(url, data=data, headers=h, method=method)
        resp = urllib.request.urlopen(r)
        status = resp.status
        payload = json.loads(resp.read().decode())
        ok = status == expect
        if ok:
            PASS += 1
            print(f"  [OK] {method} {path} -> {status}")
        else:
            FAIL += 1
            print(f"  [FAIL] {method} {path} -> expected {expect}, got {status}")
        return payload, status
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            payload = json.loads(e.read().decode())
        except Exception:
            payload = {}
        ok = status == expect
        if ok:
            PASS += 1
            print(f"  [OK] {method} {path} -> {status}")
        else:
            FAIL += 1
            print(f"  [FAIL] {method} {path} -> expected {expect}, got {status}: {payload.get('detail', '')}")
        return payload, status


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def server_available() -> bool:
    try:
        urllib.request.urlopen("http://localhost:8000/health", timeout=2)
        return True
    except Exception:
        return False


def main():
    global PASS, FAIL
    # ============================================================
    section("0. PRE-FLIGHT")
    # ============================================================
    if not server_available():
        print("  SKIP: live server not reachable at http://localhost:8000")
        print("  Start the full stack (docker compose up) to run integration tests.")
        sys.exit(0)

    # ============================================================
    section("1. HEALTH CHECK")
    # ============================================================

    r = urllib.request.urlopen("http://localhost:8000/health")
    assert r.status == 200, "Health check failed"
    data = json.loads(r.read().decode())
    assert data["status"] == "healthy"
    PASS += 1
    print("  [OK] GET /health -> 200")

    # ============================================================
    section("2. AUTH FLOW")
    # ============================================================

    user_tag = f"inttest_{int(time.time())}"
    payload, _ = req("POST", "/auth/register", {
        "username": user_tag,
        "email": f"{user_tag}@test.com",
        "password": "StrongPass123!",
    }, expect=201)
    assert payload["username"] == user_tag
    user_id = payload["id"]

    req("POST", "/auth/register", {
        "username": user_tag,
        "email": f"{user_tag}2@test.com",
        "password": "StrongPass123!",
    }, expect=409)

    payload, _ = req("POST", "/auth/login", {
        "username": user_tag,
        "password": "StrongPass123!",
    })
    access_token = payload["access_token"]
    refresh_token = payload["refresh_token"]
    assert payload["token_type"] == "bearer"

    req("POST", "/auth/login", {
        "username": user_tag,
        "password": "wrong",
    }, expect=401)

    payload, _ = req("GET", "/auth/me", token=access_token)
    assert payload["username"] == user_tag
    assert payload["id"] == user_id

    req("GET", "/auth/me", expect=401)

    payload, _ = req("POST", "/auth/refresh", {
        "refresh_token": refresh_token,
    })
    assert "access_token" in payload

    req("POST", "/auth/change-password", {
        "current_password": "StrongPass123!",
        "new_password": "NewStrongPass456!",
    }, token=access_token)

    payload, _ = req("POST", "/auth/login", {
        "username": user_tag,
        "password": "NewStrongPass456!",
    })
    access_token2 = payload["access_token"]

    print(f"\n  Auth Summary: user_id={user_id}")

    # ============================================================
    section("3. CHAT FLOW")
    # ============================================================

    payload, _ = req("POST", "/chat/conversations", {
        "title": "Integration Test Chat",
    }, token=access_token2, expect=201)
    conv_id = payload["id"]
    assert payload["title"] == "Integration Test Chat"
    print(f"  Conversation ID: {conv_id}")

    payload, _ = req("GET", "/chat/conversations", token=access_token2)
    assert len(payload) >= 1
    found = any(c["id"] == conv_id for c in payload)
    assert found, "Created conversation not in list"

    payload, _ = req("GET", f"/chat/conversations/{conv_id}/messages", token=access_token2)
    assert isinstance(payload, list)
    assert len(payload) == 0

    payload, _ = req("POST", f"/chat/conversations/{conv_id}/messages", {
        "message": "Hello, this is an integration test.",
        "stream": False,
    }, token=access_token2)
    assert payload["role"] == "assistant"
    print(f"  Message response: {len(payload['content'])} chars")

    # ============================================================
    section("4. TRAINING FLOW")
    # ============================================================

    payload, _ = req("POST", "/training/datasets", {
        "name": "Integration Test Dataset",
        "description": "Created during integration tests",
    }, token=access_token2, expect=201)
    ds_id = payload["id"]
    assert payload["name"] == "Integration Test Dataset"
    print(f"  Dataset ID: {ds_id}")

    payload, _ = req("GET", "/training/datasets", token=access_token2)
    assert len(payload) >= 1
    found = any(d["id"] == ds_id for d in payload)
    assert found, "Created dataset not in list"

    payload, _ = req("GET", f"/training/datasets/{ds_id}", token=access_token2)
    assert payload["id"] == ds_id

    payload, _ = req("GET", "/training/versions", token=access_token2)
    assert isinstance(payload, dict)
    assert "versions" in payload
    assert "total" in payload

    # ============================================================
    section("5. UNLEARNING FLOW")
    # ============================================================

    payload, _ = req("POST", "/unlearning/requests", {
        "sample_ids": [1, 2, 3],
        "algorithm": "sisa",
        "reason": "Integration test deletion",
    }, token=access_token2, expect=201)
    req_id = payload["id"]
    assert payload["algorithm"] == "sisa"
    assert payload["status"] == "pending"
    print(f"  Request ID: {req_id}")

    payload, _ = req("GET", "/unlearning/requests", token=access_token2)
    assert len(payload) >= 1

    payload, _ = req("GET", f"/unlearning/requests/{req_id}", token=access_token2)
    assert payload["id"] == req_id

    payload, _ = req("POST", f"/unlearning/requests/{req_id}/execute", token=access_token2)
    assert payload["status"] == "completed"
    print(f"  Unlearning result ID: {payload.get('result_id')}")

    payload, _ = req("GET", f"/unlearning/results/{req_id}", token=access_token2)
    assert payload["request_id"] == req_id
    print(f"  MIA before acc: {payload.get('mia_before_accuracy')}")
    print(f"  MIA after acc:  {payload.get('mia_after_accuracy')}")
    print(f"  Merkle root:    {payload.get('merkle_root', '')[:20]}...")
    print(f"  Signature:      {payload.get('signature', '')[:20]}...")

    # ============================================================
    section("6. SUMMARY")
    # ============================================================
    print(f"\n  Passed: {PASS}")
    print(f"  Failed: {FAIL}")
    print(f"  Total:  {PASS + FAIL}")

    if FAIL > 0:
        sys.exit(1)
    else:
        print("\n  ✅ ALL INTEGRATION TESTS PASSED")


if __name__ == "__main__":
    main()
