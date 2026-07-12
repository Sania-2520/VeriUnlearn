from __future__ import annotations

import random
import string

from locust import HttpUser, task, between


class VeriUnlearnUser(HttpUser):
    wait_time = between(1, 3)
    token = None
    user_id = None

    def on_start(self):
        username = "loadtest_" + "".join(random.choices(string.ascii_lowercase, k=8))
        email = f"{username}@test.com"

        res = self.client.post("/api/v1/auth/register", json={
            "username": username,
            "email": email,
            "password": "testpass123",
        })
        if res.status_code == 201:
            login_res = self.client.post("/api/v1/auth/login", json={
                "username": username,
                "password": "testpass123",
            })
            if login_res.status_code == 200:
                self.token = login_res.json().get("access_token")
                self.user_id = login_res.json().get("user", {}).get("id")

    def _headers(self):
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    @task(5)
    def health(self):
        self.client.get("/health")

    @task(3)
    def list_conversations(self):
        self.client.get("/api/v1/chat/conversations", headers=self._headers())

    @task(2)
    def create_conversation(self):
        self.client.post("/api/v1/chat/conversations", headers=self._headers(), json={
            "title": "Load Test Conversation",
        })

    @task(2)
    def send_message(self):
        conv_res = self.client.post("/api/v1/chat/conversations", headers=self._headers(), json={
            "title": "Load Test",
        })
        if conv_res.status_code == 201:
            conv_id = conv_res.json()["id"]
            self.client.post(f"/api/v1/chat/conversations/{conv_id}/messages", headers=self._headers(), json={
                "content": "Hello, this is a load test message.",
            })

    @task(1)
    def list_datasets(self):
        self.client.get("/api/v1/training/datasets", headers=self._headers())

    @task(1)
    def list_versions(self):
        self.client.get("/api/v1/training/versions", headers=self._headers())

    @task(1)
    def list_documents(self):
        self.client.get("/api/v1/documents", headers=self._headers())

    @task(1)
    def usage(self):
        self.client.get("/api/v1/usage/me", headers=self._headers())
