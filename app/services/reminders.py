from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import ApplicationRequest, ApprovalDecision, Reminder, Role
from app.models.enums import AuditAction, FieldStatus, RequestStatus
from app.services import audit, mailer

logger = logging.getLogger(__name__)

FINAL_STATUSES = {
    RequestStatus.APPROVED.value,
    RequestStatus.REJECTED.value,
    RequestStatus.PROVISIONALLY_APPROVED.value,
}


def scan(session: Session, now: datetime | None = None) -> int:
    """
    Scan all non-final requests and send reminders as needed.
    Returns the number of reminders sent.
    """
    if now is None:
        now = datetime.utcnow()

    active_requests = (
        session.query(ApplicationRequest)
        .filter(ApplicationRequest.status.notin_(list(FINAL_STATUSES)))
        .filter(ApplicationRequest.status != RequestStatus.DRAFT.value)
        .filter(ApplicationRequest.status != RequestStatus.CHANGES_REQUESTED.value)
        .all()
    )

    sent = 0
    for req in active_requests:
        sent += _process_request(session, req, now)

    session.flush()
    return sent


def _process_request(session: Session, req: ApplicationRequest, now: datetime) -> int:
    sent = 0
    # Group pending decisions by role
    role_ids = {
        d.role_id
        for d in req.decisions
        if d.status in (FieldStatus.IN_PROGRESS.value, FieldStatus.IN_REVIEW.value)
    }

    for role_id in role_ids:
        sent += _check_role(session, req, role_id, now)

    return sent


def _check_role(
    session: Session,
    req: ApplicationRequest,
    role_id: int,
    now: datetime,
) -> int:
    role = session.get(Role, role_id)
    if not role:
        return 0

    # Find last decision write for this role on this request
    last_action = _last_decision_time(session, req.id, role_id) or req.submitted_at
    if not last_action:
        return 0

    days_elapsed = (now - last_action).days

    # Check what stages already sent
    stages_sent = _stages_already_sent(session, req.id, role_id)

    sent = 0

    if days_elapsed >= 14 and 3 not in stages_sent:
        _send_reminder(session, req, role, 3, now)
        sent += 1
    elif days_elapsed >= 7 and 2 not in stages_sent:
        _send_reminder(session, req, role, 2, now)
        sent += 1
    elif days_elapsed >= 3 and 1 not in stages_sent:
        # Stage 1: max 1/day
        last_stage1 = _last_reminder_of_stage(session, req.id, role_id, 1)
        if last_stage1 is None or (now - last_stage1) >= timedelta(hours=24):
            _send_reminder(session, req, role, 1, now)
            sent += 1

    return sent


def _last_decision_time(
    session: Session, request_id: int, role_id: int
) -> datetime | None:
    decision = (
        session.query(ApprovalDecision)
        .filter(
            ApprovalDecision.request_id == request_id,
            ApprovalDecision.role_id == role_id,
            ApprovalDecision.decided_at.isnot(None),
        )
        .order_by(ApprovalDecision.decided_at.desc())
        .first()
    )
    return decision.decided_at if decision else None


def _stages_already_sent(
    session: Session, request_id: int, role_id: int
) -> set[int]:
    reminders = (
        session.query(Reminder)
        .filter(
            Reminder.request_id == request_id,
            Reminder.role_id == role_id,
        )
        .all()
    )
    return {r.stage for r in reminders}


def _last_reminder_of_stage(
    session: Session, request_id: int, role_id: int, stage: int
) -> datetime | None:
    reminder = (
        session.query(Reminder)
        .filter(
            Reminder.request_id == request_id,
            Reminder.role_id == role_id,
            Reminder.stage == stage,
        )
        .order_by(Reminder.sent_at.desc())
        .first()
    )
    return reminder.sent_at if reminder else None


def _send_reminder(
    session: Session,
    req: ApplicationRequest,
    role: Role,
    stage: int,
    now: datetime,
) -> None:
    recipients: list[str] = []

    if stage in (1, 2, 3):
        # Notify role members
        for u in role.users:
            recipients.append(u.email)
        if role.notification_email:
            recipients.append(role.notification_email)

    if stage >= 2:
        # Also notify requester
        if req.requester:
            recipients.append(req.requester.email)

    if stage >= 3:
        # Admin escalation – add role notification email again (placeholder)
        pass

    recipients = list(set(recipients))

    # Record reminder in DB
    reminder = Reminder(
        request_id=req.id,
        role_id=role.id,
        stage=stage,
        sent_at=now,
        recipients_json=json.dumps(recipients),
    )
    session.add(reminder)

    # Send notifications
    subject = f"[Stufe {stage}] Erinnerung: Antrag '{req.title}' wartet auf Prüfung"
    body = (
        f"Der Antrag #{req.id} '{req.title}' wartet seit mehreren Tagen "
        f"auf eine Prüfung durch '{role.label}'. Bitte prüfen Sie zeitnah."
    )
    for email in recipients:
        mailer.would_send(session, kind=f"REMINDER_STAGE_{stage}", recipient_email=email,
                          subject=subject, body=body)

    audit.log(
        session,
        None,
        AuditAction.REMINDER_SENT.value,
        "ApplicationRequest",
        str(req.id),
        {"role": role.code, "stage": stage, "recipients": recipients},
    )
