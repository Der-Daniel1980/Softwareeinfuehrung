"""Admin-UI für den Fragenkatalog (Fragen anlegen / ändern / löschen,
Verantwortlichkeiten je Rolle festlegen)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.auth_deps import require_admin
from app.database import get_db
from app.models import User
from app.models.enums import InputType, Responsibility
from app.services import field_admin
from app.web.templates import templates

router = APIRouter(prefix="/admin/fields", tags=["web-admin-fields"])


def _input_type_choices() -> list[str]:
    return [t.value for t in InputType]


def _kind_choices() -> list[str]:
    return [Responsibility.INFO.value, Responsibility.APPROVAL.value]


@router.get("", response_class=HTMLResponse)
async def admin_fields_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> HTMLResponse:
    fields = field_admin.list_fields(db)
    roles = field_admin.list_roles(db)
    return templates.TemplateResponse(
        "admin/fields_list.html",
        {
            "request": request,
            "user": user,
            "fields": fields,
            "roles": roles,
        },
    )


@router.get("/new", response_class=HTMLResponse)
async def admin_field_new(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> HTMLResponse:
    roles = field_admin.list_roles(db)
    # Höchste sort_order + 10, damit das neue Feld am Ende steht
    existing = field_admin.list_fields(db)
    next_sort = (max((f.sort_order for f in existing), default=0) or 0) + 10
    return templates.TemplateResponse(
        "admin/fields_form.html",
        {
            "request": request,
            "user": user,
            "field": None,
            "roles": roles,
            "responsibilities": {},
            "input_types": _input_type_choices(),
            "kinds": _kind_choices(),
            "sort_default": next_sort,
            "errors": [],
        },
    )


@router.get("/{field_id}", response_class=HTMLResponse)
async def admin_field_edit(
    field_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> HTMLResponse:
    field = field_admin.get_field(db, field_id)
    roles = field_admin.list_roles(db)
    responsibilities = {r.role_id: r.kind for r in field.responsibilities}
    return templates.TemplateResponse(
        "admin/fields_form.html",
        {
            "request": request,
            "user": user,
            "field": field,
            "roles": roles,
            "responsibilities": responsibilities,
            "input_types": _input_type_choices(),
            "kinds": _kind_choices(),
            "sort_default": field.sort_order,
            "errors": [],
        },
    )


def _collect_resp_map(form: dict, role_ids: list[int]) -> dict[int, str]:
    """Lese pro Rolle ein Feld `resp_<role_id>` aus dem Formular.

    Werte: '' (keine), 'INFO', 'APPROVAL'.
    """
    out: dict[int, str] = {}
    for rid in role_ids:
        val = (form.get(f"resp_{rid}") or "").strip().upper()
        if val in ("INFO", "APPROVAL"):
            out[rid] = val
        else:
            out[rid] = ""
    return out


@router.post(
    "/new",
    response_class=HTMLResponse,
)
async def admin_field_create(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> HTMLResponse:
    form = dict(await request.form())
    roles = field_admin.list_roles(db)
    resp_map = _collect_resp_map(form, [r.id for r in roles])
    try:
        field_admin.create_field(
            db,
            user,
            key=form.get("key", "").strip(),
            section=form.get("section", "").strip(),
            label=form.get("label", "").strip(),
            help_text=form.get("help_text", "").strip() or None,
            input_type=form.get("input_type", "TEXT"),
            enum_values_json=form.get("enum_values_json", "").strip() or None,
            is_required=bool(form.get("is_required")),
            conditional_on_key=form.get("conditional_on_key", "").strip() or None,
            conditional_equals=form.get("conditional_equals", "").strip() or None,
            sort_order=int(form.get("sort_order") or 0),
            responsibilities=resp_map,
            included_in_poc=bool(form.get("included_in_poc")),
        )
    except HTTPException as e:
        db.rollback()
        errs = e.detail.get("errors") if isinstance(e.detail, dict) else [str(e.detail)]
        return templates.TemplateResponse(
            "admin/fields_form.html",
            {
                "request": request,
                "user": user,
                "field": None,
                "roles": roles,
                "responsibilities": resp_map,
                "input_types": _input_type_choices(),
                "kinds": _kind_choices(),
                "sort_default": int(form.get("sort_order") or 0),
                "errors": errs,
                "form": form,
            },
            status_code=e.status_code,
        )
    db.commit()
    return RedirectResponse(
        "/admin/fields?flash=Frage+angelegt",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post(
    "/{field_id}",
    response_class=HTMLResponse,
)
async def admin_field_update(
    field_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> HTMLResponse:
    form = dict(await request.form())
    roles = field_admin.list_roles(db)
    resp_map = _collect_resp_map(form, [r.id for r in roles])
    try:
        field_admin.update_field(
            db,
            user,
            field_id,
            section=form.get("section", "").strip(),
            label=form.get("label", "").strip(),
            help_text=form.get("help_text", "").strip() or None,
            input_type=form.get("input_type", "TEXT"),
            enum_values_json=form.get("enum_values_json", "").strip() or None,
            is_required=bool(form.get("is_required")),
            conditional_on_key=form.get("conditional_on_key", "").strip() or None,
            conditional_equals=form.get("conditional_equals", "").strip() or None,
            sort_order=int(form.get("sort_order") or 0),
            responsibilities=resp_map,
            included_in_poc=bool(form.get("included_in_poc")),
        )
    except HTTPException as e:
        db.rollback()
        errs = e.detail.get("errors") if isinstance(e.detail, dict) else [str(e.detail)]
        field = field_admin.get_field(db, field_id)
        return templates.TemplateResponse(
            "admin/fields_form.html",
            {
                "request": request,
                "user": user,
                "field": field,
                "roles": roles,
                "responsibilities": resp_map,
                "input_types": _input_type_choices(),
                "kinds": _kind_choices(),
                "sort_default": int(form.get("sort_order") or 0),
                "errors": errs,
                "form": form,
            },
            status_code=e.status_code,
        )
    db.commit()
    return RedirectResponse(
        "/admin/fields?flash=Frage+gespeichert",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post(
    "/{field_id}/delete",
    response_class=HTMLResponse,
)
async def admin_field_delete(
    field_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> HTMLResponse:
    try:
        field_admin.delete_field(db, user, field_id)
    except HTTPException as e:
        db.rollback()
        msg = (
            e.detail
            if isinstance(e.detail, str)
            else (e.detail.get("errors", ["Fehler"])[0] if isinstance(e.detail, dict) else "Fehler")
        )
        return RedirectResponse(
            f"/admin/fields?flash={msg}", status_code=status.HTTP_303_SEE_OTHER,
        )
    db.commit()
    return RedirectResponse(
        "/admin/fields?flash=Frage+gel%C3%B6scht",
        status_code=status.HTTP_303_SEE_OTHER,
    )
