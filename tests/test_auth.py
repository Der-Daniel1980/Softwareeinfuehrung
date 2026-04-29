from __future__ import annotations

from fastapi.testclient import TestClient


def test_login_success(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@demo.local", "password": "demo1234"},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    # Cookie should be set
    assert "access_token" in resp.cookies


def test_login_wrong_password(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@demo.local", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


def test_login_unknown_user(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@demo.local", "password": "demo1234"},
    )
    assert resp.status_code == 401


def test_me_unauthenticated(client: TestClient) -> None:
    # Clear cookies
    c = TestClient(client.app)
    resp = c.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_me_authenticated(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/login",
        json={"email": "admin@demo.local", "password": "demo1234"},
    )
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "admin@demo.local"
    assert "ADMIN" in data["roles"]


def test_logout(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/login",
        json={"email": "admin@demo.local", "password": "demo1234"},
    )
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    # After logout, /me should fail
    c2 = TestClient(client.app)
    resp2 = c2.get("/api/v1/auth/me")
    assert resp2.status_code == 401
