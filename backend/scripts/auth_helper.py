"""Shared helpers for verify scripts."""

from __future__ import annotations

from fastapi.testclient import TestClient


def login_headers(client: TestClient, username: str = "admin", password: str = "admin123") -> dict[str, str]:
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("code") == 0, body
    token = body["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
