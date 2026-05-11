from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import FieldDefinition, FieldResponsibility, Role
from app.models.enums import Responsibility


def approval_fields_for_role(session: Session, role_code: str) -> list[FieldDefinition]:
    """Return all fields where the given role has APPROVAL responsibility."""
    role = session.query(Role).filter(Role.code == role_code).first()
    if not role:
        return []
    resp = (
        session.query(FieldResponsibility)
        .filter(
            FieldResponsibility.role_id == role.id,
            FieldResponsibility.kind == Responsibility.APPROVAL.value,
        )
        .all()
    )
    field_ids = [r.field_id for r in resp]
    if not field_ids:
        return []
    return (
        session.query(FieldDefinition)
        .filter(FieldDefinition.id.in_(field_ids))
        .order_by(FieldDefinition.sort_order)
        .all()
    )


def info_fields_for_role(session: Session, role_code: str) -> list[FieldDefinition]:
    """Return all fields where the given role has INFO responsibility."""
    role = session.query(Role).filter(Role.code == role_code).first()
    if not role:
        return []
    resp = (
        session.query(FieldResponsibility)
        .filter(
            FieldResponsibility.role_id == role.id,
            FieldResponsibility.kind == Responsibility.INFO.value,
        )
        .all()
    )
    field_ids = [r.field_id for r in resp]
    if not field_ids:
        return []
    return (
        session.query(FieldDefinition)
        .filter(FieldDefinition.id.in_(field_ids))
        .order_by(FieldDefinition.sort_order)
        .all()
    )


def roles_that_must_approve(session: Session, field_key: str) -> list[Role]:
    """Return all roles that have APPROVAL responsibility for the given field key."""
    field = session.query(FieldDefinition).filter(FieldDefinition.key == field_key).first()
    if not field:
        return []
    resp = (
        session.query(FieldResponsibility)
        .filter(
            FieldResponsibility.field_id == field.id,
            FieldResponsibility.kind == Responsibility.APPROVAL.value,
        )
        .all()
    )
    role_ids = [r.role_id for r in resp]
    if not role_ids:
        return []
    return session.query(Role).filter(Role.id.in_(role_ids)).all()


def sections_for_request(
    session: Session,
    req: object,
    viewer_role_codes: list[str],
) -> list[dict]:
    """
    Return a list of sections with fields filtered by viewer's responsibilities.
    REQUESTER, ADMIN, AUDITOR see everything.
    Reviewer roles see their F-fields (editable) + I-fields (read-only).
    Fields with no responsibility for the viewer are hidden.
    """
    is_privileged = any(
        c in viewer_role_codes for c in ("REQUESTER", "ADMIN", "AUDITOR")
    )
    all_fields = (
        session.query(FieldDefinition).order_by(FieldDefinition.sort_order).all()
    )

    # POC-Modus: vereinfachter Antrag, der nur ausgewählte Felder zeigt.
    # Ein Feld ist im POC sichtbar, wenn:
    #   – `included_in_poc = True` ODER
    #   – es ein Conditional-Trigger eines anderen included_in_poc-Feldes ist
    #     (sonst hängt das bedingte Feld in der Luft).
    is_poc = bool(getattr(req, "is_poc", False))
    poc_keys: set[str] = set()
    if is_poc:
        poc_keys = {f.key for f in all_fields if f.included_in_poc}
        # Trigger-Keys ergänzen, damit z. B. „Begründung Kategorie D" nicht
        # ohne Auslöser ins Leere zeigt.
        trigger_keys = {
            f.conditional_on_key
            for f in all_fields
            if f.included_in_poc and f.conditional_on_key
        }
        poc_keys |= {k for k in trigger_keys if k}

    sections: dict[str, list[dict]] = {}
    for field in all_fields:
        if is_poc and field.key not in poc_keys:
            continue

        if is_privileged:
            editable = True
            visible = True
        else:
            visible = False
            editable = False
            for resp in field.responsibilities:
                if resp.role.code in viewer_role_codes:
                    visible = True
                    if resp.kind == Responsibility.APPROVAL.value:
                        editable = True

        if not visible:
            continue

        sections.setdefault(field.section, []).append(
            {"field": field, "editable": editable}
        )

    return [
        {"section": sec, "fields": items} for sec, items in sections.items()
    ]
