"""
Happy path + rejection + multi-member role tests.
"""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import as_role, get_test_db

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_all_f_field_role_pairs(db: Session) -> list[tuple[str, int]]:
    """Return all (field_key, role_id) pairs with APPROVAL responsibility."""
    from app.models import FieldResponsibility
    from app.models.enums import Responsibility

    resps = (
        db.query(FieldResponsibility)
        .filter(FieldResponsibility.kind == Responsibility.APPROVAL.value)
        .all()
    )
    from app.models import FieldDefinition

    result = []
    for resp in resps:
        field = db.get(FieldDefinition, resp.field_id)
        if field:
            result.append((field.key, resp.role_id))
    return result


def fill_all_required_fields(client: TestClient, req_id: int) -> None:
    """Fill all required fields with dummy values."""
    from app.models import FieldDefinition
    from app.models.enums import InputType

    db = get_test_db()
    try:
        fields = (
            db.query(FieldDefinition)
            .filter(FieldDefinition.is_required.is_(True))
            .all()
        )
        for f in fields:
            val = "test_value"
            if f.input_type == InputType.NUMBER.value:
                val = "10"
            elif f.input_type == InputType.YESNO.value:
                val = "nein"
            elif f.input_type == InputType.DATE.value:
                val = "2026-12-01"
            elif f.input_type == InputType.ENUM.value and f.enum_values:
                import json
                opts = json.loads(f.enum_values)
                val = opts[0] if opts else "test"
            elif f.conditional_on_key:
                continue  # skip conditional required fields (they won't be checked if condition not met)
            client.patch(
                f"/api/v1/requests/{req_id}/fields/{f.key}",
                json={"value": val},
            )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Happy path: DRAFT → SUBMIT → all roles approve → APPROVED
# ---------------------------------------------------------------------------


def test_full_happy_path(client: TestClient) -> None:
    as_role(client, "REQUESTER")

    # 1. Create draft
    resp = client.post("/api/v1/requests", json={"title": "Happy path test"})
    assert resp.status_code == 201, resp.text
    req_id = resp.json()["id"]

    # 2. Set system_category = B
    client.patch(f"/api/v1/requests/{req_id}", json={"system_category": "B"})

    # 3. Set application owner + IT owner
    db = get_test_db()
    try:
        from app.models import User
        owner = db.query(User).filter(User.email == "owner@demo.local").first()
        it_owner = db.query(User).filter(User.email == "appop@demo.local").first()
        client.patch(
            f"/api/v1/requests/{req_id}",
            json={
                "application_owner_id": owner.id,
                "it_application_owner_id": it_owner.id,
            },
        )
    finally:
        db.close()

    # 4. Fill all required fields
    fill_all_required_fields(client, req_id)

    # 5. Submit
    resp = client.post(f"/api/v1/requests/{req_id}/submit", json={"category_d_confirmed_by": []})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "IN_REVIEW"

    # 6. Get decisions
    resp = client.get(f"/api/v1/requests/{req_id}/decisions")
    assert resp.status_code == 200
    decisions = resp.json()
    assert len(decisions) > 0

    # 7. All roles approve all their fields
    role_email_map = {
        "BETRIEBSRAT": "br@demo.local",
        "IT_SECURITY": "itsec@demo.local",
        "DATA_PROTECTION": "dsb@demo.local",
        "APP_MANAGER": "appmgr@demo.local",
        "APP_OPERATION": "appop@demo.local",
        "LICENSE_MGMT": "lic@demo.local",
    }

    for decision in decisions:
        db2 = get_test_db()
        try:
            from app.models import Role
            role = db2.get(Role, decision["role_id"])
            if not role:
                continue
            email = role_email_map.get(role.code)
            if not email:
                continue
        finally:
            db2.close()

        as_role(client, role.code)
        client.post(
            f"/api/v1/requests/{req_id}/decisions",
            json={
                "field_key": decision["field_key"],
                "role_id": decision["role_id"],
                "status": "APPROVED",
            },
        )
        # May already be approved - ignore 4xx if decision gone to APPROVED
        # Just check for 200 or already-approved state

    # 8. Check final status
    as_role(client, "REQUESTER")
    resp = client.get(f"/api/v1/requests/{req_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"

    # 9. Catalog entry created
    resp = client.get("/api/v1/catalog")
    assert resp.status_code == 200
    entries = resp.json()
    req_entries = [e for e in entries if e["request_id"] == req_id]
    assert len(req_entries) == 1


# ---------------------------------------------------------------------------
# Rejection flow
# ---------------------------------------------------------------------------


def test_rejection_flow(client: TestClient) -> None:
    as_role(client, "REQUESTER")

    # Create and submit
    resp = client.post("/api/v1/requests", json={"title": "Rejection test"})
    req_id = resp.json()["id"]
    client.patch(f"/api/v1/requests/{req_id}", json={"system_category": "B"})
    db = get_test_db()
    try:
        from app.models import User
        owner = db.query(User).filter(User.email == "owner@demo.local").first()
        it_owner = db.query(User).filter(User.email == "appop@demo.local").first()
        client.patch(
            f"/api/v1/requests/{req_id}",
            json={
                "application_owner_id": owner.id,
                "it_application_owner_id": it_owner.id,
            },
        )
    finally:
        db.close()
    fill_all_required_fields(client, req_id)
    resp = client.post(f"/api/v1/requests/{req_id}/submit", json={"category_d_confirmed_by": []})
    assert resp.status_code == 200, resp.text

    # Get a field that APP_MANAGER must approve
    resp = client.get(f"/api/v1/requests/{req_id}/decisions")
    decisions = resp.json()
    db2 = get_test_db()
    try:
        from app.models import Role
        appmgr_role = db2.query(Role).filter(Role.code == "APP_MANAGER").first()
        appmgr_decision = next(
            (d for d in decisions if d["role_id"] == appmgr_role.id), None
        )
    finally:
        db2.close()

    assert appmgr_decision is not None

    # APP_MANAGER rejects one field
    as_role(client, "APP_MANAGER")
    resp = client.post(
        f"/api/v1/requests/{req_id}/decisions",
        json={
            "field_key": appmgr_decision["field_key"],
            "role_id": appmgr_decision["role_id"],
            "status": "REJECTED",
            "comment": "Please fix this field",
        },
    )
    assert resp.status_code == 200, resp.text

    # Request should be CHANGES_REQUESTED
    as_role(client, "REQUESTER")
    resp = client.get(f"/api/v1/requests/{req_id}")
    assert resp.json()["status"] == "CHANGES_REQUESTED"

    # Requester updates the field
    client.patch(
        f"/api/v1/requests/{req_id}/fields/{appmgr_decision['field_key']}",
        json={"value": "updated_value"},
    )

    # Resubmit
    resp = client.post(f"/api/v1/requests/{req_id}/resubmit", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] == "IN_REVIEW"

    # Check that the previously rejected decision is now IN_REVIEW (reset)
    resp = client.get(f"/api/v1/requests/{req_id}/decisions")
    decisions_after = resp.json()
    reset_decision = next(
        (d for d in decisions_after
         if d["field_key"] == appmgr_decision["field_key"]
         and d["role_id"] == appmgr_decision["role_id"]),
        None,
    )
    assert reset_decision is not None
    assert reset_decision["status"] == "IN_REVIEW"


# ---------------------------------------------------------------------------
# One APPROVED in multi-member role is sufficient
# ---------------------------------------------------------------------------


def test_one_approval_in_role_sufficient(client: TestClient) -> None:
    """Add a second BR user; first BR approves → should be enough."""
    # Add second BR member via admin
    as_role(client, "ADMIN")
    db = get_test_db()
    try:
        from app.models import Role
        br_role = db.query(Role).filter(Role.code == "BETRIEBSRAT").first()
        br_role_id = br_role.id
    finally:
        db.close()

    resp = client.post(
        "/api/v1/users",
        json={
            "email": "br2@demo.local",
            "name": "BR Zweiter",
            "password": "demo1234",
            "role_codes": ["BETRIEBSRAT"],
        },
    )
    assert resp.status_code in (201, 409), resp.text  # 409 if already exists

    # Create and submit a request
    as_role(client, "REQUESTER")
    resp = client.post("/api/v1/requests", json={"title": "Multi-member BR test"})
    req_id = resp.json()["id"]
    client.patch(f"/api/v1/requests/{req_id}", json={"system_category": "B"})
    db = get_test_db()
    try:
        from app.models import User
        owner = db.query(User).filter(User.email == "owner@demo.local").first()
        it_owner = db.query(User).filter(User.email == "appop@demo.local").first()
        client.patch(
            f"/api/v1/requests/{req_id}",
            json={
                "application_owner_id": owner.id,
                "it_application_owner_id": it_owner.id,
            },
        )
    finally:
        db.close()
    fill_all_required_fields(client, req_id)
    client.post(f"/api/v1/requests/{req_id}/submit", json={"category_d_confirmed_by": []})

    # Approve all fields with the FIRST BR user (br@demo.local)
    as_role(client, "BETRIEBSRAT")
    resp = client.get(f"/api/v1/requests/{req_id}/decisions")
    decisions = resp.json()
    br_decisions = [d for d in decisions if d["role_id"] == br_role_id]
    for d in br_decisions:
        client.post(
            f"/api/v1/requests/{req_id}/decisions",
            json={
                "field_key": d["field_key"],
                "role_id": d["role_id"],
                "status": "APPROVED",
            },
        )

    # br@demo.local approval should be sufficient (OR logic)
    resp = client.get(f"/api/v1/requests/{req_id}/decisions")
    br_decisions_after = [
        d for d in resp.json() if d["role_id"] == br_role_id
    ]
    # All BR decisions should be APPROVED (same decisions, only one user in DB for BR at approval time)
    assert all(d["status"] == "APPROVED" for d in br_decisions_after)
