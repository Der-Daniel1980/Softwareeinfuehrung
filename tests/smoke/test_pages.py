"""Smoke tests for all web pages — one GET per route per role."""
from __future__ import annotations

import pytest

from tests.conftest import as_role  # noqa: F401

# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    # Re-use the session-scoped client from conftest
    import tests.conftest as conf
    return conf.TestClient if hasattr(conf, "TestClient") else _get_client()


def _get_client():
    from fastapi.testclient import TestClient as TC

    from app.database import get_db
    from app.main import app
    from tests.conftest import override_get_db
    app.dependency_overrides[get_db] = override_get_db
    return TC(app, raise_server_exceptions=True)


# Use a module-level client so we share login cookies
_client = _get_client()


def login(email: str, password: str = "demo1234") -> None:
    resp = _client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"


# ── Unauthenticated redirect ────────────────────────────────────────────────

def test_unauthed_root_returns_401_or_redirect():
    # Fresh client with no cookies — backend raises 401 (no redirect configured)
    from fastapi.testclient import TestClient as TC

    from app.database import get_db
    from app.main import app
    from tests.conftest import override_get_db
    app.dependency_overrides[get_db] = override_get_db
    c = TC(app, raise_server_exceptions=False, follow_redirects=False)
    resp = c.get("/")
    # Backend returns 401 for unauthenticated web requests
    assert resp.status_code in (401, 302, 303, 307), (
        f"Expected 401 or redirect, got {resp.status_code}"
    )


def test_login_page_renders():
    c = _get_client()
    resp = c.get("/login")
    assert resp.status_code == 200
    assert "SysIntro" in resp.text
    assert "demo1234" in resp.text


# ── REQUESTER role pages ────────────────────────────────────────────────────

class TestRequesterPages:
    @classmethod
    def setup_class(cls):
        login("requester@demo.local")

    def test_dashboard(self):
        resp = _client.get("/")
        assert resp.status_code == 200
        assert "Dashboard" in resp.text

    def test_requests_list(self):
        resp = _client.get("/requests")
        assert resp.status_code == 200

    def test_requests_new_get(self):
        resp = _client.get("/requests/new")
        assert resp.status_code == 200
        assert "Neuer Antrag" in resp.text

    def test_catalog(self):
        resp = _client.get("/catalog")
        assert resp.status_code == 200

    def test_admin_users_forbidden(self):
        resp = _client.get("/admin/users", follow_redirects=False)
        assert resp.status_code in (403, 302, 307)

    def test_admin_audit_forbidden(self):
        resp = _client.get("/admin/audit", follow_redirects=False)
        assert resp.status_code in (403, 302, 307)


# ── ADMIN role pages ────────────────────────────────────────────────────────

class TestAdminPages:
    @classmethod
    def setup_class(cls):
        login("admin@demo.local")

    def test_dashboard(self):
        resp = _client.get("/")
        assert resp.status_code == 200
        assert "Dashboard" in resp.text

    def test_requests_list(self):
        resp = _client.get("/requests")
        assert resp.status_code == 200

    def test_catalog(self):
        resp = _client.get("/catalog")
        assert resp.status_code == 200

    def test_admin_users(self):
        resp = _client.get("/admin/users")
        assert resp.status_code == 200
        assert "Benutzerverwaltung" in resp.text

    def test_admin_audit(self):
        resp = _client.get("/admin/audit")
        assert resp.status_code == 200
        assert "Auditlog" in resp.text


# ── AUDITOR role pages ──────────────────────────────────────────────────────

class TestAuditorPages:
    @classmethod
    def setup_class(cls):
        login("auditor@demo.local")

    def test_dashboard(self):
        resp = _client.get("/")
        assert resp.status_code == 200
        assert "Dashboard" in resp.text

    def test_requests_list(self):
        resp = _client.get("/requests")
        assert resp.status_code == 200

    def test_catalog(self):
        resp = _client.get("/catalog")
        assert resp.status_code == 200

    def test_admin_audit(self):
        resp = _client.get("/admin/audit")
        assert resp.status_code == 200
        assert "Auditlog" in resp.text

    def test_admin_users_forbidden(self):
        resp = _client.get("/admin/users", follow_redirects=False)
        assert resp.status_code in (403, 302, 307)


# ── Reviewer roles ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("email", [
    "br@demo.local",
    "itsec@demo.local",
    "dsb@demo.local",
    "appmgr@demo.local",
    "appop@demo.local",
    "lic@demo.local",
])
def test_reviewer_dashboard_and_requests(email):
    login(email)
    resp = _client.get("/")
    assert resp.status_code == 200
    assert "Dashboard" in resp.text

    resp2 = _client.get("/requests")
    assert resp2.status_code == 200

    resp3 = _client.get("/catalog")
    assert resp3.status_code == 200

    # Admin pages should be forbidden
    resp4 = _client.get("/admin/users", follow_redirects=False)
    assert resp4.status_code in (403, 302, 307)

    resp5 = _client.get("/admin/audit", follow_redirects=False)
    assert resp5.status_code in (403, 302, 307)


# ── Request create + edit flow (REQUESTER) ──────────────────────────────────

class TestRequestFlow:
    req_id: int | None = None

    @classmethod
    def setup_class(cls):
        login("requester@demo.local")

    def test_create_request_post(self):
        resp = _client.post(
            "/requests/new",
            data={"title": "Smoke-Test Antrag"},
            follow_redirects=False,
        )
        assert resp.status_code in (302, 303), f"Expected redirect, got {resp.status_code}: {resp.text}"
        location = resp.headers.get("location", "")
        assert "/requests/" in location
        # Extract req_id
        TestRequestFlow.req_id = int(location.rstrip("/").split("/")[-1])

    def test_edit_page_loads(self):
        assert TestRequestFlow.req_id is not None
        resp = _client.get(f"/requests/{TestRequestFlow.req_id}")
        assert resp.status_code == 200
        assert "Smoke-Test Antrag" in resp.text

    def test_revisions_page_loads(self):
        assert TestRequestFlow.req_id is not None
        resp = _client.get(f"/requests/{TestRequestFlow.req_id}/revisions")
        assert resp.status_code == 200
        assert "Verlauf" in resp.text
