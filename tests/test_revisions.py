"""Tests for field revision creation."""
from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import as_role


def test_patch_field_creates_revision(client: TestClient) -> None:
    as_role(client, "REQUESTER")

    # Create a request
    resp = client.post("/api/v1/requests", json={"title": "Revision test"})
    req_id = resp.json()["id"]

    # Set a field value
    resp1 = client.patch(
        f"/api/v1/requests/{req_id}/fields/produkt.name",
        json={"value": "First value"},
    )
    assert resp1.status_code == 200

    # Change the field value
    resp2 = client.patch(
        f"/api/v1/requests/{req_id}/fields/produkt.name",
        json={"value": "Second value"},
    )
    assert resp2.status_code == 200

    # Check revisions
    resp3 = client.get(f"/api/v1/requests/{req_id}/revisions")
    assert resp3.status_code == 200
    revisions = resp3.json()
    assert len(revisions) >= 2

    # Find revision for produkt.name with old/new values
    name_revisions = [r for r in revisions if r.get("field_key") == "produkt.name"]
    assert len(name_revisions) >= 1

    # Second revision should have old=First value, new=Second value
    second_rev = next(
        (r for r in name_revisions if r.get("old_value") == "First value"), None
    )
    assert second_rev is not None
    assert second_rev["new_value"] == "Second value"


def test_get_specific_revision(client: TestClient) -> None:
    as_role(client, "REQUESTER")
    resp = client.post("/api/v1/requests", json={"title": "Rev lookup test"})
    req_id = resp.json()["id"]

    client.patch(
        f"/api/v1/requests/{req_id}/fields/produkt.name",
        json={"value": "rev1"},
    )

    resp = client.get(f"/api/v1/requests/{req_id}/revisions")
    revisions = resp.json()
    assert len(revisions) >= 1

    rev_num = revisions[0]["revision_number"]
    resp2 = client.get(f"/api/v1/requests/{req_id}/revisions/{rev_num}")
    assert resp2.status_code == 200
    assert resp2.json()["revision_number"] == rev_num
