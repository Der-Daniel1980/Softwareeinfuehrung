from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth_deps import require_admin
from app.core.csrf import verify_api_csrf
from app.database import get_db
from app.models import Reminder
from app.services import reminders as reminder_svc

router = APIRouter(tags=["reminders"])


@router.get("/reminders")
def list_reminders(
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
) -> list[dict]:
    rems = db.query(Reminder).order_by(Reminder.sent_at.desc()).all()
    return [
        {
            "id": r.id,
            "request_id": r.request_id,
            "role_id": r.role_id,
            "stage": r.stage,
            "sent_at": r.sent_at.isoformat() if r.sent_at else None,
            "recipients_json": r.recipients_json,
        }
        for r in rems
    ]


@router.post("/admin/run-reminder-scan", dependencies=[Depends(verify_api_csrf)])
def run_reminder_scan(
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
) -> dict:
    sent = reminder_svc.scan(db)
    db.commit()
    return {"ok": True, "reminders_sent": sent}
