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

    sections: dict[str, list[dict]] = {}
    for field in all_fields:
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
