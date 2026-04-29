from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import ApplicationRequest, Attachment
from app.models.enums import AttachmentPurpose, RequestStatus


def validate_for_submit(session: Session, req: ApplicationRequest) -> list[str]:
    """Return a list of validation error messages (empty = OK)."""
    errors: list[str] = []

    if not req.system_category:
        errors.append("Systemkategorie (A/B/C/D) muss gesetzt sein.")

    if req.system_category == "C":
        bv = (
            session.query(Attachment)
            .filter(
                Attachment.request_id == req.id,
                Attachment.purpose == AttachmentPurpose.OPERATING_AGREEMENT.value,
            )
            .first()
        )
        if not bv:
            errors.append(
                "Kategorie C: Betriebsvereinbarung als Anhang erforderlich."
            )

    if req.system_category == "D":
        if not req.post_approval_due_date:
            # Will be auto-set by apply_category_effects, but if validate is called before that:
            pass  # allowed – apply_category_effects will set it
        if not req.short_description:
            errors.append("Kategorie D: Kurzbeschreibung (short_description) erforderlich.")
        # Check justification field value
        from app.models import FieldValue
        justification = (
            session.query(FieldValue)
            .filter(
                FieldValue.request_id == req.id,
                FieldValue.field_key == "system_category.justification",
            )
            .first()
        )
        if not justification or not (justification.value_text or "").strip():
            errors.append("Kategorie D: Begründung (system_category.justification) erforderlich.")

    return errors


def apply_category_effects(
    session: Session,
    req: ApplicationRequest,
    submit_actor_ids: list[int] | None = None,
) -> None:
    """
    Apply side effects based on system_category.
    - A: BR decisions will be set to ACKNOWLEDGED (done after decisions are created)
    - D: set status to PROVISIONALLY_APPROVED, set post_approval_due_date
    """
    from app.models.enums import FieldStatus

    if req.system_category == "A":
        # Mark all BR approval decisions as ACKNOWLEDGED
        from app.models import ApprovalDecision, Role

        br_role = session.query(Role).filter(Role.code == "BETRIEBSRAT").first()
        if br_role:
            br_decisions = (
                session.query(ApprovalDecision)
                .filter(
                    ApprovalDecision.request_id == req.id,
                    ApprovalDecision.role_id == br_role.id,
                )
                .all()
            )
            for d in br_decisions:
                d.status = FieldStatus.ACKNOWLEDGED.value

    if req.system_category == "D":
        req.status = RequestStatus.PROVISIONALLY_APPROVED.value
        if not req.post_approval_due_date:
            req.post_approval_due_date = datetime.utcnow() + timedelta(days=30)
