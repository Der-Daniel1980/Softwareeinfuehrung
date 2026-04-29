from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import ApplicationRequest, Revision, User
from app.models.enums import RevisionKind


def _next_revision_number(session: Session, request_id: int) -> int:
    from sqlalchemy import func

    result = (
        session.query(func.max(Revision.revision_number))
        .filter(Revision.request_id == request_id)
        .scalar()
    )
    return (result or 0) + 1


def record_field_change(
    session: Session,
    req: ApplicationRequest,
    field_key: str,
    old: str | None,
    new: str | None,
    actor: User,
    summary: str,
) -> Revision:
    rev = Revision(
        request_id=req.id,
        revision_number=_next_revision_number(session, req.id),
        kind=RevisionKind.FIELD_CHANGE.value,
        field_key=field_key,
        old_value=old,
        new_value=new,
        summary=summary,
        created_by=actor.id,
    )
    session.add(rev)
    return rev


def snapshot(
    session: Session,
    req: ApplicationRequest,
    actor: User,
    summary: str,
) -> Revision:
    """Create a full JSON snapshot of all field values + decisions."""
    field_values = {fv.field_key: fv.value_text for fv in req.field_values}
    decisions = [
        {
            "field_key": d.field_key,
            "role_id": d.role_id,
            "status": d.status,
            "decided_by": d.decided_by,
        }
        for d in req.decisions
    ]
    snap = {
        "status": req.status,
        "system_category": req.system_category,
        "field_values": field_values,
        "decisions": decisions,
    }
    rev = Revision(
        request_id=req.id,
        revision_number=_next_revision_number(session, req.id),
        kind=RevisionKind.SUBMIT_SNAPSHOT.value,
        snapshot_json=json.dumps(snap),
        summary=summary,
        created_by=actor.id,
    )
    session.add(rev)
    return rev
