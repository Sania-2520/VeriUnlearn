from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_user_cannot_access_other_users_conversations(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "username": "isolation_user1",
        "email": "user1@test.com",
        "password": "password123",
    })
    await client.post("/api/v1/auth/register", json={
        "username": "isolation_user2",
        "email": "user2@test.com",
        "password": "password123",
    })

    resp1 = await client.post("/api/v1/auth/login", json={
        "username": "isolation_user1",
        "password": "password123",
    })
    resp2 = await client.post("/api/v1/auth/login", json={
        "username": "isolation_user2",
        "password": "password123",
    })

    headers1 = {"Authorization": f"Bearer {resp1.json()['access_token']}"}
    headers2 = {"Authorization": f"Bearer {resp2.json()['access_token']}"}

    res1 = await client.post("/api/v1/chat/conversations", headers=headers1, json={"title": "User1 Conv"})
    assert res1.status_code == 201
    conv1_id = res1.json()["id"]

    res2 = await client.get(f"/api/v1/chat/conversations/{conv1_id}/messages", headers=headers2)
    assert res2.status_code in (403, 404)


@pytest.mark.asyncio
async def test_user_cannot_access_other_users_documents(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "username": "doc_user1",
        "email": "doc1@test.com",
        "password": "password123",
    })
    await client.post("/api/v1/auth/register", json={
        "username": "doc_user2",
        "email": "doc2@test.com",
        "password": "password123",
    })

    resp1 = await client.post("/api/v1/auth/login", json={
        "username": "doc_user1",
        "password": "password123",
    })
    resp2 = await client.post("/api/v1/auth/login", json={
        "username": "doc_user2",
        "password": "password123",
    })

    headers1 = {"Authorization": f"Bearer {resp1.json()['access_token']}"}
    headers2 = {"Authorization": f"Bearer {resp2.json()['access_token']}"}

    res1 = await client.post(
        "/api/v1/documents/upload",
        headers=headers1,
        files={"file": ("test.txt", b"test content", "text/plain")},
    )
    if res1.status_code == 201:
        doc_id = res1.json()["id"]
        res2 = await client.get(f"/api/v1/documents/{doc_id}", headers=headers2)
        assert res2.status_code in (403, 404)


@pytest.mark.asyncio
async def test_admin_cannot_access_user_api_keys(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "username": "admin_isolation",
        "email": "admin@test.com",
        "password": "password123",
        "role": "admin",
    })
    await client.post("/api/v1/auth/register", json={
        "username": "key_user",
        "email": "key@test.com",
        "password": "password123",
    })

    admin_resp = await client.post("/api/v1/auth/login", json={
        "username": "admin_isolation",
        "password": "password123",
    })
    user_resp = await client.post("/api/v1/auth/login", json={
        "username": "key_user",
        "password": "password123",
    })

    admin_headers = {"Authorization": f"Bearer {admin_resp.json()['access_token']}"}
    user_headers = {"Authorization": f"Bearer {user_resp.json()['access_token']}"}

    res1 = await client.post("/api/v1/api-keys", headers=user_headers, json={"name": "test_key"})
    if res1.status_code == 201:
        key_id = res1.json()["id"]
        res2 = await client.get(f"/api/v1/api-keys/{key_id}", headers=admin_headers)
        assert res2.status_code in (403, 404)
