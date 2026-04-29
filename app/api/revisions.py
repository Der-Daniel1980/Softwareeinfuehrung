from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth_deps import get_current_user
from app.database import get_db
from app.models import ApplicationRequest, Revision, User
from app.services import workflow

router = APIRouter(tags=["revisions"])


@router.get("/requests/{req_id}/revisions")
def list_revisions(
    req_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    req = _get_req_or_404(db, req_id)
    if not workflow.can_view(req, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    revs = (
        db.query(Revision)
        .filter(Revision.request_id == req_id)
        .order_by(Revision.revision_number)
        .all()
    )
    return [_to_dict(r) for r in revs]


@router.get("/requests/{req_id}/revisions/{rev_num}")
def get_revision(
    req_id: int,
    rev_num: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    req = _get_req_or_404(db, req_id)
    if not workflow.can_view(req, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    rev = (
        db.query(Revision)
        .filter(
            Revision.request_id == req_id,
            Revision.revision_number == rev_num,
        )
        .first()
    )
    if not rev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return _to_dict(rev)


def _get_req_or_404(db: Session, req_id: int) -> ApplicationRequest:
    req = db.get(ApplicationRequest, req_id)
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return req


def _to_dict(r: Revision) -> dict:
    return {
        "id": r.id,
        "request_id": r.request_id,
        "revision_number": r.revision_number,
        "kind": r.kind,
        "field_key": r.field_key,
        "old_value": r.old_value,
        "new_value": r.new_value,
        "snapshot_json": r.snapshot_json,
        "summary": r.summary,
        "created_by": r.created_by,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
