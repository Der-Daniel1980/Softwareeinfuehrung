from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.auth_deps import get_current_user
from app.core.csrf import verify_api_csrf
from app.database import get_db
from app.models import ApplicationRequest, Comment, User
from app.models.enums import AuditAction
from app.schemas.comment import CommentCreate, CommentRead
from app.services import audit, workflow

router = APIRouter(tags=["comments"])


@router.get("/requests/{req_id}/comments", response_model=list[CommentRead])
def get_comments(
    req_id: int,
    field_key: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CommentRead]:
    """List comments on a request. If ``field_key`` is provided, only that
    field's thread is returned. Sorted ascending so the UI can render a
    natural conversation."""
    req = _get_req_or_404(db, req_id)
    if not workflow.can_view(req, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    q = db.query(Comment).filter(Comment.request_id == req_id)
    if field_key is not None:
        q = q.filter(Comment.field_key == field_key)
    comments = q.order_by(Comment.created_at).all()
    return [_to_read(c) for c in comments]


@router.post("/requests/{req_id}/comments", response_model=CommentRead,
             status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(verify_api_csrf)])
async def add_comment(
    req_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CommentRead:
    """Accepts JSON or form-encoded so HTMX, fetch and traditional forms work."""
    ct = (request.headers.get("content-type") or "").lower()
    if ct.startswith("application/json"):
        try:
            data = await request.json()
        except Exception:
            data = {}
        if not isinstance(data, dict):
            data = {}
    else:
        form = await request.form()
        data = {k: v for k, v in form.items()}
    body_text = str(data.get("body") or "").strip()
    if not body_text:
        raise HTTPException(status_code=422, detail="Kommentar darf nicht leer sein")

    field_key = data.get("field_key") or None
    role_raw = data.get("role_id")
    parent_raw = data.get("parent_id")
    role_id = int(role_raw) if role_raw not in (None, "", "null") else None
    parent_id = int(parent_raw) if parent_raw not in (None, "", "null") else None

    req = _get_req_or_404(db, req_id)
    if not workflow.can_view(req, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    # role_id must match an actual role of the user (prevents impersonation)
    if role_id is not None:
        user_role_ids = {r.id for r in user.roles}
        if role_id not in user_role_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of the specified role",
            )

    comment = Comment(
        request_id=req_id,
        field_key=field_key,
        role_id=role_id,
        parent_id=parent_id,
        author_id=user.id,
        body=body_text,
        created_at=datetime.utcnow(),
    )
    db.add(comment)
    audit.log(db, user, AuditAction.COMMENT_ADDED.value, "Comment", str(req_id),
              {"field_key": field_key})
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
