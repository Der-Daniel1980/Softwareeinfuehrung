from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth_deps import get_current_user
from app.database import get_db
from app.models import ApplicationRequest, User
from app.schemas.decision import DecisionRead, DecisionSet
from app.services import workflow

router = APIRouter(tags=["decisions"])


@router.get("/requests/{req_id}/decisions", response_model=list[DecisionRead])
def get_decisions(
    req_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DecisionRead]:
    req = _get_req_or_404(db, req_id)
    if not workflow.can_view(req, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return [
        DecisionRead(
            id=d.id,
            request_id=d.request_id,
            field_key=d.field_key,
            role_id=d.role_id,
            status=d.status,
            decided_by=d.decided_by,
            decided_at=d.decided_at,
            comment=d.comment,
        )
        for d in req.decisions
    ]


@router.post("/requests/{req_id}/decisions", response_model=DecisionRead)
def set_decision(
    req_id: int,
    body: DecisionSet,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DecisionRead:
    req = _get_req_or_404(db, req_id)
    decision = workflow.set_decision(
        db, req, body.field_key, body.role_id, body.status, body.comment, user
    )
    db.commit()
    db.refresh(decision)
    return DecisionRead(
        id=decision.id,
        request_id=decision.request_id,
        field_key=decision.field_key,
        role_id=decision.role_id,
        status=decision.status,
        decided_by=decision.decided_by,
        decided_at=decision.decided_at,
        comment=decision.comment,
    )


def _get_req_or_404(db: Session, req_id: int) -> ApplicationRequest:
    req = db.get(ApplicationRequest, req_id)
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    return req
