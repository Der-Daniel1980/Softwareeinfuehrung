from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.auth_deps import get_current_user
from app.database import get_db
from app.models import ApplicationRequest, FieldDefinition, Revision, User
from app.services import responsibility, workflow
from app.web.templates import templates

router = APIRouter(prefix="/requests", tags=["web-requests"])


@router.get("", response_class=HTMLResponse)
async def requests_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    all_reqs = db.query(ApplicationRequest).all()
    visible = [r for r in all_reqs if workflow.can_view(r, user)]
    return templates.TemplateResponse(
        "requests/list.html",
        {"request": request, "user": user, "requests": visible, "now": datetime.utcnow},
    )


@router.get("/new", response_class=HTMLResponse)
async def request_new(
    request: Request,
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    return templates.TemplateResponse(
        "requests/new.html", {"request": request, "user": user}
    )


@router.post("/new", response_class=HTMLResponse)
async def request_new_submit(
    request: Request,
    title: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    req = ApplicationRequest(
        title=title,
        requester_id=user.id,
        created_at=datetime.utcnow(),
    )
    db.add(req)
    db.flush()
    db.commit()
    db.refresh(req)
    return RedirectResponse(url=f"/requests/{req.id}", status_code=303)  # type: ignore[return-value]


@router.get("/{req_id}", response_class=HTMLResponse)
async def request_detail(
    req_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    req = db.get(ApplicationRequest, req_id)
    if not req or not workflow.can_view(req, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    role_codes = user.role_codes()
    sections = responsibility.sections_for_request(db, req, role_codes)
    all_fields = db.query(FieldDefinition).order_by(FieldDefinition.sort_order).all()
    field_values = {fv.field_key: fv.value_text for fv in req.field_values}
    return templates.TemplateResponse(
        "requests/edit.html",
        {
            "request": request,
            "user": user,
            "req": req,
            "sections": sections,
            "all_fields": all_fields,
            "field_values": field_values,
            "role_codes": role_codes,
        },
    )


@router.get("/{req_id}/review", response_class=HTMLResponse)
async def request_review(
    req_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    req = db.get(ApplicationRequest, req_id)
    if not req or not workflow.can_view(req, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    role_codes = user.role_codes()
    sections = responsibility.sections_for_request(db, req, role_codes)
    field_values = {fv.field_key: fv.value_text for fv in req.field_values}
    # decisions keyed by (field_key, role_id)
    decisions = {(d.field_key, d.role_id): d for d in req.decisions}
    return templates.TemplateResponse(
        "requests/review.html",
        {
            "request": request,
            "user": user,
            "req": req,
            "sections": sections,
            "field_values": field_values,
            "decisions": decisions,
            "role_codes": role_codes,
        },
    )


@router.get("/{req_id}/revisions", response_class=HTMLResponse)
async def request_revisions(
    req_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    req = db.get(ApplicationRequest, req_id)
    if not req or not workflow.can_view(req, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    revisions = (
        db.query(Revision)
        .filter(Revision.request_id == req_id)
        .order_by(Revision.revision_number.desc())
        .all()
    )
    return templates.TemplateResponse(
        "requests/revisions.html",
        {"request": request, "user": user, "req": req, "revisions": revisions},
    )
