"""Tests that INFO-role cannot set decisions."""
from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import as_role, get_test_db


def test_info_role_cannot_set_decision(client: TestClient) -> None:
    """
    LICENSE_MGMT has INFO responsibility for 'produkt.beschreibung'.
    It should get 403 when trying to set a decision on that field.
    """
    as_role(client, "REQUESTER")
    resp = client.post("/api/v1/requests", json={"title": "Info role test"})
    req_id = resp.json()["id"]

    db = get_test_db()
    try:
        from app.models import FieldDefinition, FieldResponsibility, Role, User
        from app.models.enums import Responsibility

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

        from tests.test_workflow import fill_all_required_fields
        fill_all_required_fields(client, req_id)
        client.post(f"/api/v1/requests/{req_id}/submit", json={"category_d_confirmed_by": []})

        # Find a field where LICENSE_MGMT has INFO (not APPROVAL)
        lic_role = db.query(Role).filter(Role.code == "LICENSE_MGMT").first()
        info_field_resp = (
            db.query(FieldResponsibility)
            .filter(
                FieldResponsibility.role_id == lic_role.id,
                FieldResponsibility.kind == Responsibility.INFO.value,
            )
            .first()
        )
        assert info_field_resp is not None

        field = db.get(FieldDefinition, info_field_resp.field_id)
        field_key = field.key
        lic_role_id = lic_role.id
    finally:
        db.close()

    # Try to set decision as LICENSE_MGMT on an INFO field
    as_role(client, "LICENSE_MGMT")
    resp = client.post(
        f"/api/v1/requests/{req_id}/decisions",
        json={
            "field_key": field_key,
            "role_id": lic_role_id,
            "status": "APPROVED",
        },
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
