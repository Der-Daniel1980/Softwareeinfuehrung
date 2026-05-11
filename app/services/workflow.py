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
    """Visibility check.

    DESIGN NOTE (intentional, documented in docs/SECURITY.md): A reviewer with
    any APPROVAL or INFO responsibility on a request sees the FULL request,
    including fields where their role has neither I nor F responsibility.

    This mirrors the spec's Excel template where every reviewer sees the
    complete form for context — they need to read related fields to make a
    sensible decision on their own. If field-level confidentiality is later
    required, filter `field_values` in `_to_read()` per role.
    """
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
    """Wer darf welches Feld noch ändern.

    DRAFT/CHANGES_REQUESTED = uneingeschränkte Bearbeitung wie bisher.
    SUBMITTED/IN_REVIEW     = Antragsteller darf weiterhin Felder pflegen
                              (z. B. Reaktion auf Rückfragen ohne BLOCKER-
                              Workflow). Jede Änderung wird in `revisions`
                              protokolliert, damit Reviewer den vorherigen
                              Stand jederzeit nachvollziehen können.
    APPROVED/REJECTED/WITHDRAWN = endgültig, schreibgeschützt.
    """
    if user.has_role("ADMIN"):
        return True
    if req.requester_id != user.id:
        return False
    return req.status in (
        RequestStatus.DRAFT.value,
        RequestStatus.CHANGES_REQUESTED.value,
        RequestStatus.SUBMITTED.value,
        RequestStatus.IN_REVIEW.value,
    )


def can_withdraw(req: ApplicationRequest, user: User) -> bool:
    """Antragsteller (oder ADMIN) darf einen noch offenen Antrag zurückziehen."""
    if user.has_role("ADMIN"):
        return req.status not in (
            RequestStatus.APPROVED.value,
            RequestStatus.WITHDRAWN.value,
        )
    if req.requester_id != user.id:
        return False
    return req.status in (
        RequestStatus.SUBMITTED.value,
        RequestStatus.IN_REVIEW.value,
        RequestStatus.CHANGES_REQUESTED.value,
        RequestStatus.PROVISIONALLY_APPROVED.value,
    )


def can_delete(req: ApplicationRequest, user: User) -> bool:
    """Nur DRAFT-Anträge dürfen physisch gelöscht werden — und nur vom
    Antragsteller selbst (oder ADMIN). Alles andere ist auditrelevant und
    bleibt erhalten (siehe `withdraw`)."""
    if req.status != RequestStatus.DRAFT.value:
        return False
    return user.has_role("ADMIN") or req.requester_id == user.id


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
    """Pflichtfelder validieren. Im POC-Modus werden nur Felder mit
    `included_in_poc=True` betrachtet."""

    q = session.query(FieldDefinition).filter(FieldDefinition.is_required.is_(True))
    if req.is_poc:
        q = q.filter(FieldDefinition.included_in_poc.is_(True))
    fields = q.all()
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
    """ApprovalDecision-Zeilen pro (F-Feld × F-Rolle) anlegen.

    Im POC-Workflow werden ausschließlich Felder mit `included_in_poc=True`
    in den Reviewer-Workflow aufgenommen — der Sinn des POC ist gerade, dass
    nicht alle Rollen jedes Detail prüfen müssen.
    """
    q = (
        session.query(FieldResponsibility, FieldDefinition)
        .join(FieldDefinition, FieldDefinition.id == FieldResponsibility.field_id)
        .filter(FieldResponsibility.kind == Responsibility.APPROVAL.value)
    )
    if req.is_poc:
        q = q.filter(FieldDefinition.included_in_poc.is_(True))

    existing = {(d.field_key, d.role_id) for d in req.decisions}
    for fr, field in q.all():
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
        # No stub yet – create one. Stubs are normally produced by `submit()`,
        # but a request can also be set to a reviewable status by alternative
        # means (e.g. seeded demo data). Auto-creating here keeps the API
        # idempotent and lets reviewers act on any field they're authorised for.
        decision = ApprovalDecision(
            request_id=req.id,
            field_key=field_key,
            role_id=role_id,
            status=new_status,
            decided_by=actor.id,
            decided_at=datetime.utcnow(),
            comment=comment,
        )
        session.add(decision)
        old_status = None
    else:
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


# ---------------------------------------------------------------------------
# Withdraw / Delete
# ---------------------------------------------------------------------------


def withdraw(
    session: Session,
    req: ApplicationRequest,
    actor: User,
    reason: str | None = None,
) -> ApplicationRequest:
    """Antragsteller zieht einen offenen Antrag zurück.

    Status -> WITHDRAWN. Daten bleiben erhalten (Revisions-Historie weiter
    sichtbar, Reviewer sehen den Antrag im Read-Only-Modus). Wir legen einen
    Snapshot mit Begründung an, damit der Auditor nachvollziehen kann, in
    welchem Zustand der Antrag zurückgezogen wurde.
    """
    if not can_withdraw(req, actor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Antrag kann in diesem Status nicht zurückgezogen werden.",
        )

    req.status = RequestStatus.WITHDRAWN.value

    summary = "Antrag zurückgezogen"
    if reason:
        summary = f"{summary}: {reason[:300]}"
    revisions.snapshot(session, req, actor, summary)
    audit.log(
        session,
        actor,
        AuditAction.REQUEST_WITHDRAWN.value,
        "ApplicationRequest",
        str(req.id),
        {"action": "withdraw", "reason": reason or ""},
    )
    session.flush()
    return req


def delete_draft(
    session: Session,
    req: ApplicationRequest,
    actor: User,
) -> None:
    """Physisch löschen – nur für DRAFT.

    Räumt alle abhängigen Tabellen mit, damit FK-Constraints nicht zuschnappen
    und keine Karteileichen zurückbleiben.
    """
    if not can_delete(req, actor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur eigene Entwürfe können gelöscht werden.",
        )

    # Audit zuerst, danach gibt es das Objekt nicht mehr.
    audit.log(
        session,
        actor,
        AuditAction.REQUEST_DELETED.value,
        "ApplicationRequest",
        str(req.id),
        {"action": "delete_draft", "title": req.title},
    )

    # Abhängigkeiten manuell – ORM-Cascade ist nicht überall gesetzt.
    from app.models import (
        ApprovalDecision as _AD,
        Attachment as _Att,
        Comment as _C,
        FieldValue as _FV,
        Reminder as _R,
        Revision as _Rev,
    )

    session.query(_FV).filter(_FV.request_id == req.id).delete(synchronize_session=False)
    session.query(_AD).filter(_AD.request_id == req.id).delete(synchronize_session=False)
    session.query(_C).filter(_C.request_id == req.id).delete(synchronize_session=False)
    session.query(_Att).filter(_Att.request_id == req.id).delete(synchronize_session=False)
    session.query(_R).filter(_R.request_id == req.id).delete(synchronize_session=False)
    session.query(_Rev).filter(_Rev.request_id == req.id).delete(synchronize_session=False)
    # request_owner_deputies + request_bit_fc sind reine Verknüpfungstabellen
    from sqlalchemy import text as _text
    session.execute(
        _text("DELETE FROM request_owner_deputies WHERE request_id = :rid"),
        {"rid": req.id},
    )
    session.execute(
        _text("DELETE FROM request_bit_fc WHERE request_id = :rid"),
        {"rid": req.id},
    )

    session.delete(req)
    session.flush()


# ---------------------------------------------------------------------------
# POC → Standard-Antrag promovieren
# ---------------------------------------------------------------------------


def promote_poc_to_standard(
    session: Session,
    poc_req: ApplicationRequest,
    actor: User,
) -> ApplicationRequest:
    """Aus einem POC einen vollwertigen Standard-Antrag erzeugen.

    Erzeugt eine Kopie des Antrags mit `is_poc=False`, übernimmt:
    - alle Feldwerte (auch die, die im POC nicht abgefragt wurden – sie
      bleiben einfach leer und können noch befüllt werden)
    - Stamm-Daten (Title, Owner, IT-Owner, Beschreibung, Standort, Kategorie)
    - BIT/FC-Verknüpfungen

    Erzeugt KEIN Audit-Carry-Over für Decisions / Comments – der neue Antrag
    durchläuft den vollständigen Reviewer-Workflow von vorn (das ist genau
    der Punkt: das POC hatte einen verkürzten Workflow, jetzt muss der
    Vollumfang geprüft werden).
    """
    if not poc_req.is_poc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur POC-Anträge können zu Standard-Anträgen hochgestuft werden.",
        )
    if actor.id != poc_req.requester_id and not actor.has_role("ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur Antragsteller oder Admin dürfen einen POC promovieren.",
        )

    from app.models import FieldValue as _FV
    from sqlalchemy import text as _text

    new_req = ApplicationRequest(
        title=poc_req.title,
        requester_id=poc_req.requester_id,
        status=RequestStatus.DRAFT.value,
        system_category=poc_req.system_category,
        application_owner_id=poc_req.application_owner_id,
        it_application_owner_id=poc_req.it_application_owner_id,
        short_description=poc_req.short_description,
        installation_location=poc_req.installation_location,
        is_poc=False,
        promoted_from_poc_id=poc_req.id,
        created_at=datetime.utcnow(),
    )
    session.add(new_req)
    session.flush()

    # Feldwerte 1:1 kopieren
    for fv in poc_req.field_values:
        session.add(
            _FV(
                request_id=new_req.id,
                field_key=fv.field_key,
                value_text=fv.value_text,
                updated_by=actor.id,
                updated_at=datetime.utcnow(),
            )
        )

    # BIT/FC-Verknüpfungen
    session.execute(
        _text(
            "INSERT INTO request_bit_fc (request_id, bit_fc_id) "
            "SELECT :new_id, bit_fc_id FROM request_bit_fc WHERE request_id = :old_id"
        ),
        {"new_id": new_req.id, "old_id": poc_req.id},
    )

    revisions.snapshot(
        session, new_req, actor,
        f"Aus POC #{poc_req.id} promoviert",
    )
    audit.log(
        session, actor, AuditAction.REQUEST_SUBMITTED.value,
        "ApplicationRequest", str(new_req.id),
        {"action": "promote_from_poc", "poc_id": poc_req.id},
    )
    session.flush()
    return new_req
