from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.auth_deps import get_current_user
from app.database import get_db
from app.models import ApplicationRequest, User
from app.services import progress as progress_svc
from app.services import workflow
from app.web.templates import templates

router = APIRouter(tags=["web-dashboard"])


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    all_reqs = db.query(ApplicationRequest).all()
    visible = [r for r in all_reqs if workflow.can_view(r, user)]
    # Compact per-role progress for each non-DRAFT request the user can see.
    progress_by_id = {
        r.id: progress_svc.role_progress(db, r)
        for r in visible
        if r.status != "DRAFT"
    }
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "requests": visible,
            "progress_by_id": progress_by_id,
            "now": datetime.utcnow,
        },
    )
