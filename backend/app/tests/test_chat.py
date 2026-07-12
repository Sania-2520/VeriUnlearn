from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict:
    await client.post("/api/v1/auth/register", json={
        "username": "chatuser",
        "email": "chat@example.com",
        "password": "testpassword123",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "username": "chatuser",
        "password": "testpassword123",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_conversation(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/chat/conversations",
        json={"title": "Test Conversation"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Conversation"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_conversations(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/api/v1/chat/conversations",
        json={"title": "Conv 1"},
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/chat/conversations",
        json={"title": "Conv 2"},
        headers=auth_headers,
    )

    response = await client.get("/api/v1/chat/conversations", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_rename_conversation(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/v1/chat/conversations",
        json={"title": "Old Title"},
        headers=auth_headers,
    )
    conv_id = create.json()["id"]

    response = await client.patch(
        f"/api/v1/chat/conversations/{conv_id}",
        json={"title": "New Title"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["title"] == "New Title"


@pytest.mark.asyncio
async def test_rename_conversation_not_found(client: AsyncClient, auth_headers: dict):
    response = await client.patch(
        "/api/v1/chat/conversations/99999",
        json={"title": "Ghost"},
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_conversation(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/v1/chat/conversations",
        json={"title": "Delete Me"},
        headers=auth_headers,
    )
    conv_id = create.json()["id"]

    response = await client.delete(
        f"/api/v1/chat/conversations/{conv_id}",
        headers=auth_headers,
    )
    assert response.status_code == 204

    list_resp = await client.get("/api/v1/chat/conversations", headers=auth_headers)
    ids = [c["id"] for c in list_resp.json()]
    assert conv_id not in ids


@pytest.mark.asyncio
async def test_delete_conversation_not_found(client: AsyncClient, auth_headers: dict):
    response = await client.delete(
        "/api/v1/chat/conversations/99999",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_send_message_non_stream(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/v1/chat/conversations",
        json={"title": "Chat Test"},
        headers=auth_headers,
    )
    conv_id = create.json()["id"]

    response = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        json={"message": "Hello", "stream": False},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "assistant"
    assert len(data["content"]) > 0
    assert "message_id" in data


@pytest.mark.asyncio
async def test_send_message_invalid_conv(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/chat/conversations/99999/messages",
        json={"message": "Hello", "stream": False},
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_send_message_unauthorized(client: AsyncClient):
    create = await client.post(
        "/api/v1/chat/conversations",
        json={"title": "Unauth Test"},
        headers={"Authorization": "Bearer fake"},
    )
    assert create.status_code == 401
