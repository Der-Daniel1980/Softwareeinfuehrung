"""Tests for category A/B/C/D specific logic."""
from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import as_role, get_test_db


def _make_submitted_request(client: TestClient, category: str, title: str) -> tuple[int, int]:
    """Helper: create, fill, and submit a request with the given category.
    Returns (req_id, owner_id).
    """
    as_role(client, "REQUESTER")
    resp = client.post("/api/v1/requests", json={"title": title})
    req_id = resp.json()["id"]

    db = get_test_db()
    try:
        from app.models import User
        owner = db.query(User).filter(User.email == "owner@demo.local").first()
        it_owner = db.query(User).filter(User.email == "appop@demo.local").first()
        owner_id = owner.id
        it_owner_id = it_owner.id
    finally:
        db.close()

    client.patch(
        f"/api/v1/requests/{req_id}",
        json={
            "system_category": category,
            "application_owner_id": owner_id,
            "it_application_owner_id": it_owner_id,
            "short_description": "Test system for category logic",
        },
    )

    # Fill required fields
    from tests.test_workflow import fill_all_required_fields
    fill_all_required_fields(client, req_id)

    # Also fill justification for cat D
    if category == "D":
        client.patch(
            f"/api/v1/requests/{req_id}/fields/system_category.justification",
            json={"value": "Emergency justification for testing"},
        )

    return req_id, owner_id, it_owner_id


def test_category_c_without_bv_attachment_blocked(client: TestClient) -> None:
    req_id, owner_id, it_owner_id = _make_submitted_request(client, "C", "Cat C no BV")

    # Submit without uploading BV attachment
    resp = client.post(f"/api/v1/requests/{req_id}/submit", json={"category_d_confirmed_by": []})
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    errors = detail["errors"] if isinstance(detail, dict) else []
    assert any("Betriebsvereinbarung" in e for e in errors)


def test_category_c_with_bv_attachment_ok(client: TestClient) -> None:
    req_id, owner_id, it_owner_id = _make_submitted_request(client, "C", "Cat C with BV")

    # Upload a BV attachment
    import io
    fake_pdf = io.BytesIO(b"%PDF-1.4 fake pdf content")
    resp = client.post(
        f"/api/v1/requests/{req_id}/attachments?purpose=OPERATING_AGREEMENT",
        files={"file": ("bv.pdf", fake_pdf, "application/pdf")},
    )
    assert resp.status_code == 201, resp.text

    # Now submit should succeed
    resp = client.post(f"/api/v1/requests/{req_id}/submit", json={"category_d_confirmed_by": []})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "IN_REVIEW"


def test_category_d_without_owner_confirm_fails(client: TestClient) -> None:
    req_id, owner_id, it_owner_id = _make_submitted_request(client, "D", "Cat D no confirm")

    # Submit without confirming both owners
    resp = client.post(f"/api/v1/requests/{req_id}/submit", json={"category_d_confirmed_by": []})
    assert resp.status_code == 403


def test_category_d_with_confirm_provisionally_approved(client: TestClient) -> None:
    req_id, owner_id, it_owner_id = _make_submitted_request(client, "D", "Cat D with confirm")

    # Submit with both owners confirming
    resp = client.post(
        f"/api/v1/requests/{req_id}/submit",
        json={"category_d_confirmed_by": [owner_id, it_owner_id]},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "PROVISIONALLY_APPROVED"
    # post_approval_due_date should be set
    assert data["post_approval_due_date"] is not None


def test_category_a_br_decisions_acknowledged_on_submit(client: TestClient) -> None:
    req_id, owner_id, it_owner_id = _make_submitted_request(client, "A", "Cat A BR acknowledged")

    resp = client.post(f"/api/v1/requests/{req_id}/submit", json={"category_d_confirmed_by": []})
    assert resp.status_code == 200, resp.text

    # Get decisions – BR decisions should all be ACKNOWLEDGED
    resp = client.get(f"/api/v1/requests/{req_id}/decisions")
    assert resp.status_code == 200
    decisions = resp.json()

    db = get_test_db()
    try:
        from app.models import Role
        br_role = db.query(Role).filter(Role.code == "BETRIEBSRAT").first()
        br_role_id = br_role.id
    finally:
        db.close()

    br_decisions = [d for d in decisions if d["role_id"] == br_role_id]
    assert len(br_decisions) > 0, "BR should have decisions"
    for d in br_decisions:
        assert d["status"] == "ACKNOWLEDGED", f"BR decision not ACKNOWLEDGED: {d}"
