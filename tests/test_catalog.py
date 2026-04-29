"""Tests for catalog promotion and CSV export."""
from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import as_role, get_test_db


def _fully_approve_request(client: TestClient, req_id: int) -> None:
    """Approve all pending decisions for a request."""
    role_email_map = {
        "BETRIEBSRAT": "br@demo.local",
        "IT_SECURITY": "itsec@demo.local",
        "DATA_PROTECTION": "dsb@demo.local",
        "APP_MANAGER": "appmgr@demo.local",
        "APP_OPERATION": "appop@demo.local",
        "LICENSE_MGMT": "lic@demo.local",
    }
    as_role(client, "REQUESTER")
    resp = client.get(f"/api/v1/requests/{req_id}/decisions")
    decisions = resp.json()

    for decision in decisions:
        db = get_test_db()
        try:
            from app.models import Role
            role = db.get(Role, decision["role_id"])
            role_code = role.code if role else None
        finally:
            db.close()

        if not role_code or role_code not in role_email_map:
            continue

        as_role(client, role_code)
        client.post(
            f"/api/v1/requests/{req_id}/decisions",
            json={
                "field_key": decision["field_key"],
                "role_id": decision["role_id"],
                "status": "APPROVED",
            },
        )


def test_approved_request_promoted_to_catalog(client: TestClient) -> None:
    """After full approval, a catalog entry should exist."""
    as_role(client, "REQUESTER")
    resp = client.post("/api/v1/requests", json={"title": "Catalog promotion test"})
    req_id = resp.json()["id"]

    db = get_test_db()
    try:
        from app.models import User
        owner = db.query(User).filter(User.email == "owner@demo.local").first()
        it_owner = db.query(User).filter(User.email == "appop@demo.local").first()
        client.patch(
            f"/api/v1/requests/{req_id}",
            json={
                "system_category": "B",
                "application_owner_id": owner.id,
                "it_application_owner_id": it_owner.id,
            },
        )
    finally:
        db.close()

    from tests.test_workflow import fill_all_required_fields
    fill_all_required_fields(client, req_id)

    resp = client.post(f"/api/v1/requests/{req_id}/submit", json={"category_d_confirmed_by": []})
    assert resp.status_code == 200, resp.text

    _fully_approve_request(client, req_id)

    # Verify APPROVED
    as_role(client, "REQUESTER")
    resp = client.get(f"/api/v1/requests/{req_id}")
    assert resp.json()["status"] == "APPROVED"

    # Verify catalog entry
    resp = client.get("/api/v1/catalog")
    entries = resp.json()
    req_entries = [e for e in entries if e["request_id"] == req_id]
    assert len(req_entries) == 1
    assert req_entries[0]["source"] == "FROM_REQUEST"
    assert req_entries[0]["status"] == "ACTIVE"


def test_catalog_csv_export_non_empty(client: TestClient) -> None:
    """After at least one approval, CSV export should be non-empty."""
    as_role(client, "REQUESTER")
    resp = client.get("/api/v1/catalog/export.csv")
    assert resp.status_code == 200
    # Should have at least a header row
    content = resp.text
    assert "id" in content
    assert len(content.strip().splitlines()) >= 1


def test_catalog_import(client: TestClient) -> None:
    """Admin can import a catalog entry directly."""
    as_role(client, "ADMIN")
    resp = client.post(
        "/api/v1/catalog/import",
        json={"name": "Legacy System", "vendor": "OldCorp", "version": "1.0"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["source"] == "IMPORTED"
    assert data["name"] == "Legacy System"
