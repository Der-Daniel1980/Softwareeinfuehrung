from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import (
    ApplicationRequest,
    ApprovalDecision,
    FieldDefinition,
    FieldResponsibility,
    Role,
    User,
)
from app.models.enums import AuditAction, FieldStatus, RequestStatus, Responsibility
from app.services import audit, category_logic, mailer, revisions

# ---------------------------------------------------------------------------
# Visibility / edit guards
# ---------------------------------------------------------------------------


def can_view(req: ApplicationRequest, user: User) -> bool:
    if user.has_role("ADMIN") or user.has_role("AUDITOR"):
        return True
    if req.requester_id == user.id:
        return True
    # Reviewer roles see SUBMITTED+ requests where their role has any responsibility
    if req.status == RequestStatus.DRAFT.value:
        return False
    reviewer_codes = {
        "BETRIEBSRAT", "IT_SECURITY", "DATA_PROTECTION",
        "APP_MANAGER", "APP_OPERATION", "LICENSE_MGMT",
    }
    for d in req.decisions:
        if d.role and d.role.code in reviewer_codes and user.has_role(d.role.code):
            return True
    return False


def can_edit(req: ApplicationRequest, user: User) -> bool:
    if user.has_role("ADMIN"):
        return True
    return req.requester_id == user.id and req.status in (
        RequestStatus.DRAFT.value,
        RequestStatus.CHANGES_REQUESTED.value,
    )


# ---------------------------------------------------------------------------
# Submit
# ---------------------------------------------------------------------------


def submit(
    session: Session,
    req: ApplicationRequest,
    actor: User,
    category_d_confirmed_by: list[int] | None = None,
) -> ApplicationRequest:
    if req.status != RequestStatus.DRAFT.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit request in status {req.status}",
        )

    # Validate required fields
    errors = _validate_required_fields(session, req)
    cat_errors = category_logic.validate_for_submit(session, req)
    errors.extend(cat_errors)

    # Category D: four-eyes confirmation
    if req.system_category == "D":
        confirmed = set(category_d_confirmed_by or [])
        required = set(
            filter(
                None,
                [req.application_owner_id, req.it_application_owner_id],
            )
        )
        if not required or not required.issubset(confirmed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Kategorie D: Bestätigung durch Application Owner "
                    "und IT Application Owner erforderlich."
                ),
            )

    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"errors": errors},
        )

    # Transition status
    req.status = RequestStatus.IN_REVIEW.value
    req.submitted_at = datetime.utcnow()

    # Create ApprovalDecision for every (F-field × F-role) combo
    _create_decisions(session, req)

    # Category-specific effects (A: acknowledge BR; D: provisionally approve)
    category_logic.apply_category_effects(session, req)

    # Snapshot
    revisions.snapshot(session, req, actor, "Antrag eingereicht")

    # Audit
    audit.log(
        session,
        actor,
        AuditAction.REQUEST_SUBMITTED.value,
        "ApplicationRequest",
        str(req.id),
        {"status": req.status, "system_category": req.system_category},
    )

    # Notifications
    _notify_submit(session, req)

    session.flush()
    return req


def _validate_required_fields(session: Session, req: ApplicationRequest) -> list[str]:
    """Check that all unconditionally required fields have values."""

    fields = session.query(FieldDefinition).filter(FieldDefinition.is_required.is_(True)).all()
    fv_map = {fv.field_key: fv.value_text for fv in req.field_values}
    errors = []
    for field in fields:
        # Skip conditional fields where condition isn't met
        if field.conditional_on_key:
            cond_val = fv_map.get(field.conditional_on_key)
            if cond_val != field.conditional_equals:
                continue
        val = fv_map.get(field.key)
        if not val or not val.strip():
            errors.append(f"Pflichtfeld fehlt: {field.label} ({field.key})")
    return errors


def _create_decisions(session: Session, req: ApplicationRequest) -> None:
    """Create ApprovalDecision rows for every (F-field × F-role) combo."""
    f_responsibilities = (
        session.query(FieldResponsibility)
        .filter(FieldResponsibility.kind == Responsibility.APPROVAL.value)
        .all()
    )
    existing = {(d.field_key, d.role_id) for d in req.decisions}
    field_map = {
        fr.field_id: session.get(FieldDefinition, fr.field_id) for fr in f_responsibilities
    }

    for fr in f_responsibilities:
        field = field_map.get(fr.field_id)
        if not field:
            continue
        if (field.key, fr.role_id) in existing:
            continue
        decision = ApprovalDecision(
            request_id=req.id,
            field_key=field.key,
            role_id=fr.role_id,
            status=FieldStatus.IN_PROGRESS.value,
        )
        session.add(decision)

    session.flush()
    # Refresh decisions on req
    session.refresh(req)


def _notify_submit(session: Session, req: ApplicationRequest) -> None:
    """Queue notifications to all F-role members."""
    role_ids = {d.role_id for d in req.decisions}
    roles = session.query(Role).filter(Role.id.in_(role_ids)).all()
    for role in roles:
        emails = {u.email for u in role.users}
        if role.notification_email:
            emails.add(role.notification_email)
        for email in emails:
            mailer.would_send(
                session,
                kind="REQUEST_SUBMITTED",
                recipient_email=email,
                subject=f"Neuer Antrag zur Prüfung: {req.title}",
                body=f"Antrag #{req.id} '{req.title}' wurde eingereicht und wartet auf Ihre Prüfung.",
            )


# ---------------------------------------------------------------------------
# Set decision
# ---------------------------------------------------------------------------


def set_decision(
    session: Session,
    req: ApplicationRequest,
    field_key: str,
    role_id: int,
    new_status: str,
    comment: str | None,
    actor: User,
) -> ApprovalDecision:
    # Actor must be a member of the role
    role = session.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if not actor.has_role(role.code):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this role",
        )

    # Role must have APPROVAL responsibility on this field
    field = session.query(FieldDefinition).filter(FieldDefinition.key == field_key).first()
    if not field:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Field not found")
    resp = (
        session.query(FieldResponsibility)
        .filter(
            FieldResponsibility.field_id == field.id,
            FieldResponsibility.role_id == role_id,
            FieldResponsibility.kind == Responsibility.APPROVAL.value,
        )
        .first()
    )
    if not resp:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This role has only INFO (not APPROVAL) responsibility for this field",
        )

    if new_status == FieldStatus.REJECTED.value and not comment:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Comment is required when rejecting",
        )

    decision = (
        session.query(ApprovalDecision)
        .filter(
            ApprovalDecision.request_id == req.id,
            ApprovalDecision.field_key == field_key,
            ApprovalDecision.role_id == role_id,
        )
        .first()
    )
    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found"
        )

    old_status = decision.status
    decision.status = new_status
    decision.decided_by = actor.id
    decision.decided_at = datetime.utcnow()
    if comment is not None:
        decision.comment = comment

    audit.log(
        session,
        actor,
        AuditAction.DECISION_SET.value,
        "ApprovalDecision",
        str(decision.id),
        {
            "field_key": field_key,
            "role": role.code,
            "old_status": old_status,
            "new_status": new_status,
        },
    )

    session.flush()
    session.refresh(req)
    recompute_overall_status(session, req)
    return decision


# ---------------------------------------------------------------------------
# Recompute overall status
# ---------------------------------------------------------------------------


def recompute_overall_status(session: Session, req: ApplicationRequest) -> None:
    """
    After any decision change, recompute the request's overall status.
    - Any REJECTED → CHANGES_REQUESTED
    - All (F-field, F-role) pairs APPROVED or ACKNOWLEDGED → APPROVED
    """
    if req.status in (
        RequestStatus.APPROVED.value,
        RequestStatus.REJECTED.value,
        RequestStatus.DRAFT.value,
    ):
        return

    decisions = req.decisions
    if not decisions:
        return

    terminal_statuses = {FieldStatus.APPROVED.value, FieldStatus.ACKNOWLEDGED.value}

    any_rejected = any(d.status == FieldStatus.REJECTED.value for d in decisions)
    all_done = all(d.status in terminal_statuses for d in decisions)

    if any_rejected:
        if req.status != RequestStatus.CHANGES_REQUESTED.value:
            req.status = RequestStatus.CHANGES_REQUESTED.value
    elif all_done:
        req.status = RequestStatus.APPROVED.value
        req.completed_at = datetime.utcnow()
        # Promote to catalog
        from app.services.catalog import promote

        promote(session, req)
        audit.log(
            session,
            None,
            AuditAction.REQUEST_APPROVED.value,
            "ApplicationRequest",
            str(req.id),
        )

    session.flush()


# ---------------------------------------------------------------------------
# Resubmit
# ---------------------------------------------------------------------------


def resubmit(
    session: Session,
    req: ApplicationRequest,
    actor: User,
) -> ApplicationRequest:
    if req.status != RequestStatus.CHANGES_REQUESTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot resubmit request in status {req.status}",
        )

    # Reset only REJECTED decisions back to IN_REVIEW
    for decision in req.decisions:
        if decision.status == FieldStatus.REJECTED.value:
            decision.status = FieldStatus.IN_REVIEW.value
            decision.decided_by = None
            decision.decided_at = None
            decision.comment = None

    req.status = RequestStatus.IN_REVIEW.value

    revisions.snapshot(session, req, actor, "Antrag erneut eingereicht")
    audit.log(
        session,
        actor,
        AuditAction.REQUEST_SUBMITTED.value,
        "ApplicationRequest",
        str(req.id),
        {"action": "resubmit"},
    )

    _notify_resubmit(session, req)
    session.flush()
    return req


def _notify_resubmit(session: Session, req: ApplicationRequest) -> None:
    """Notify roles with IN_REVIEW decisions."""
    role_ids = {
        d.role_id
        for d in req.decisions
        if d.status == FieldStatus.IN_REVIEW.value
    }
    roles = session.query(Role).filter(Role.id.in_(role_ids)).all()
    for role in roles:
        emails = {u.email for u in role.users}
        if role.notification_email:
            emails.add(role.notification_email)
        for email in emails:
            mailer.would_send(
                session,
                kind="REQUEST_RESUBMITTED",
                recipient_email=email,
                subject=f"Antrag erneut eingereicht: {req.title}",
                body=f"Antrag #{req.id} wurde überarbeitet und wartet auf Ihre erneute Prüfung.",
            )
