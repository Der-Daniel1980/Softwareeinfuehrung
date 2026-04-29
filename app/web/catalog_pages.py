from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.auth_deps import get_current_user
from app.database import get_db
from app.models import CatalogEntry, User
from app.web.templates import templates
router = APIRouter(prefix="/catalog", tags=["web-catalog"])


@router.get("", response_class=HTMLResponse)
async def catalog_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    entries = db.query(CatalogEntry).all()
    return templates.TemplateResponse(
        "catalog/list.html", {"request": request, "user": user, "entries": entries}
    )


@router.get("/{entry_id}", response_class=HTMLResponse)
async def catalog_detail(
    entry_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    entry = db.get(CatalogEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return templates.TemplateResponse(
        "catalog/detail.html", {"request": request, "user": user, "entry": entry}
    )
