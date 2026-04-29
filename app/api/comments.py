from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth_deps import get_current_user
from app.database import get_db
from app.models import ApplicationRequest, Comment, User
from app.models.enums import AuditAction
from app.schemas.comment import CommentCreate, CommentRead
from app.services import audit, workflow

router = APIRouter(tags=["comments"])


@router.get("/requests/{req_id}/comments", response_model=list[CommentRead])
def get_comments(
    req_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CommentRead]:
    req = _get_req_or_404(db, req_id)
    if not workflow.can_view(req, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    comments = (
        db.query(Comment)
        .filter(Comment.request_id == req_id)
        .order_by(Comment.created_at)
        .all()
    )
    return [_to_read(c) for c in comments]


@router.post("/requests/{req_id}/comments", response_model=CommentRead,
             status_code=status.HTTP_201_CREATED)
def add_comment(
    req_id: int,
    body: CommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CommentRead:
    req = _get_req_or_404(db, req_id)
    if not workflow.can_view(req, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    comment = Comment(
        request_id=req_id,
        field_key=body.field_key,
        role_id=body.role_id,
        parent_id=body.parent_id,
        author_id=user.id,
        body=body.body,
        created_at=datetime.utcnow(),
    )
    db.add(comment)
    audit.log(db, user, AuditAction.COMMENT_ADDED.value, "Comment", str(req_id),
              {"field_key": body.field_key})
    db.commit()
    db.refresh(comment)
    return _to_read(comment)


def _get_req_or_404(db: Session, req_id: int) -> ApplicationRequest:
    req = db.get(ApplicationRequest, req_id)
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return req


def _to_read(c: Comment) -> CommentRead:
    return CommentRead(
        id=c.id,
        request_id=c.request_id,
        field_key=c.field_key,
        role_id=c.role_id,
        parent_id=c.parent_id,
        author_id=c.author_id,
        body=c.body,
        created_at=c.created_at,
        edited_at=c.edited_at,
    )
