"""Reminder engine tests using freezegun for time travel."""
from __future__ import annotations

from fastapi.testclient import TestClient
from freezegun import freeze_time

from tests.conftest import as_role, get_test_db


def _create_submitted_request(client: TestClient, title: str) -> int:
    """Create and submit a request, return req_id."""
    as_role(client, "REQUESTER")
    resp = client.post("/api/v1/requests", json={"title": title})
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
    assert resp.status_code == 200, f"Submit failed: {resp.text}"
    return req_id


def test_reminder_stage1_after_3_days(client: TestClient) -> None:
    """Stage 1 reminder sent after 3 days."""
    req_id = _create_submitted_request(client, "Reminder stage 1 test")

    # Time travel +3 days
    from datetime import datetime, timedelta
    future = datetime(2026, 5, 2, 7, 0, 0)  # deterministic future date

    with freeze_time(future):
        db = get_test_db()
        try:
            # Manually set submitted_at to 3 days before future
            from app.models import ApplicationRequest
            from app.services.reminders import scan
            req = db.get(ApplicationRequest, req_id)
            req.submitted_at = future - timedelta(days=3)
            db.commit()

            scan(db, now=future)
            db.commit()
        finally:
            db.close()

    # Check reminders were created
    db2 = get_test_db()
    try:
        from app.models import Reminder
        reminders = db2.query(Reminder).filter(
            Reminder.request_id == req_id,
            Reminder.stage == 1,
        ).all()
        assert len(reminders) >= 1, "Stage 1 reminder should have been sent"
    finally:
        db2.close()


def test_reminder_stage2_after_7_days(client: TestClient) -> None:
    """Stage 2 reminder sent after 7 days."""
    req_id = _create_submitted_request(client, "Reminder stage 2 test")

    from datetime import datetime, timedelta
    future = datetime(2026, 5, 7, 7, 0, 0)

    with freeze_time(future):
        db = get_test_db()
        try:
            from app.models import ApplicationRequest
            from app.services.reminders import scan
            req = db.get(ApplicationRequest, req_id)
            req.submitted_at = future - timedelta(days=7)
            db.commit()

            scan(db, now=future)
            db.commit()
        finally:
            db.close()

    db2 = get_test_db()
    try:
        from app.models import Reminder
        reminders = db2.query(Reminder).filter(
            Reminder.request_id == req_id,
            Reminder.stage == 2,
        ).all()
        assert len(reminders) >= 1, "Stage 2 reminder should have been sent"
    finally:
        db2.close()


def test_reminder_stage3_after_14_days(client: TestClient) -> None:
    """Stage 3 reminder sent after 14 days."""
    req_id = _create_submitted_request(client, "Reminder stage 3 test")

    from datetime import datetime, timedelta
    future = datetime(2026, 5, 14, 7, 0, 0)

    with freeze_time(future):
        db = get_test_db()
        try:
            from app.models import ApplicationRequest
            from app.services.reminders import scan
            req = db.get(ApplicationRequest, req_id)
            req.submitted_at = future - timedelta(days=14)
            db.commit()

            scan(db, now=future)
            db.commit()
        finally:
            db.close()

    db2 = get_test_db()
    try:
        from app.models import Reminder
        reminders = db2.query(Reminder).filter(
            Reminder.request_id == req_id,
            Reminder.stage == 3,
        ).all()
        assert len(reminders) >= 1, "Stage 3 reminder should have been sent"
    finally:
        db2.close()
