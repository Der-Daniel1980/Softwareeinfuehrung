from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.auth_deps import get_current_user
from app.database import get_db
from app.models import (
    ApplicationRequest,
    BitFcCategory,
    FieldDefinition,
    Revision,
    SystemCategoryDefinition,
    User,
    Vendor,
)
from app.services import progress as progress_svc
from app.services import responsibility, workflow
from app.web.templates import templates


def _picklist_options(db: Session) -> dict[str, list[dict]]:
    """Returns option lists for fields whose enum_values are defined dynamically.

    For Application Owner / IT Application Owner the picklist is the set of
    active users; the form still allows free text via <datalist> so demo users
    can enter a colleague's name even if they don't have an account yet.
    Future Keycloak / Entra ID integration would replace the User query with a
    directory lookup but the template does not need to change.

    For produkt.hersteller the list comes from the active Vendor master-data
    (managed under /admin/vendors). Free text remains accepted.
    """
    users = (
        db.query(User)
        .filter(User.is_active.is_(True))
        .order_by(User.name)
        .all()
    )
    bit_fc = db.query(BitFcCategory).order_by(BitFcCategory.name).all()
    vendors = (
        db.query(Vendor)
        .filter(Vendor.is_active.is_(True))
        .order_by(Vendor.name)
        .all()
    )
    return {
        "stammdaten.application_owner": [
            {"value": u.name, "label": f"{u.name} ({u.email})"} for u in users
        ],
        "stammdaten.it_application_owner": [
            {"value": u.name, "label": f"{u.name} ({u.email})"} for u in users
        ],
        "stammdaten.bit_fc": [
            {"value": c.name, "label": c.name, "description": c.description or ""}
            for c in bit_fc
        ],
        "produkt.hersteller": [
            {"value": v.name, "label": v.name + (f" – {v.description}" if v.description else "")}
            for v in vendors
        ],
    }


def _system_category_definitions(db: Session) -> list[SystemCategoryDefinition]:
    return (
        db.query(SystemCategoryDefinition)
        .order_by(SystemCategoryDefinition.code)
        .all()
    )

router = APIRouter(prefix="/requests", tags=["web-requests"])


@router.get("", response_class=HTMLResponse)
async def requests_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    all_reqs = db.query(ApplicationRequest).all()
    visible = [r for r in all_reqs if workflow.can_view(r, user)]
    # Per-request progress so the list can show "BR 2/4 offen · DSB ✓ ..." inline.
    # Skipped for DRAFTs (no review activity yet) to keep the list fast.
    progress_by_id = {
        r.id: progress_svc.role_progress(db, r)
        for r in visible
        if r.status != "DRAFT"
    }
    return templates.TemplateResponse(
        "requests/list.html",
        {
            "request": request,
            "user": user,
            "requests": visible,
            "progress_by_id": progress_by_id,
            "now": datetime.utcnow,
        },
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
    # Reviewer decisions are surfaced to the requester in edit mode so that
    # any 'Rückfrage' comment is visible inline next to the original field.
    decisions = {(d.field_key, d.role_id): d for d in req.decisions}
    role_prog = progress_svc.role_progress(db, req) if req.status != "DRAFT" else []
    return templates.TemplateResponse(
        "requests/edit.html",
        {
            "request": request,
            "user": user,
            "req": req,
            "sections": sections,
            "all_fields": all_fields,
            "field_values": field_values,
            "decisions": decisions,
            "role_progress": role_prog,
            "role_codes": role_codes,
            "picklists": _picklist_options(db),
            "system_categories": _system_category_definitions(db),
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
    role_prog = progress_svc.role_progress(db, req)
    return templates.TemplateResponse(
        "requests/review.html",
        {
            "request": request,
            "user": user,
            "req": req,
            "sections": sections,
            "field_values": field_values,
            "decisions": decisions,
            "role_progress": role_prog,
            "role_codes": role_codes,
            "picklists": _picklist_options(db),
            "system_categories": _system_category_definitions(db),
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
