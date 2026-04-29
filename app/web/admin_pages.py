from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.auth_deps import require_admin, require_admin_or_auditor
from app.database import get_db
from app.models import AuditLog, User
from app.web.templates import templates
router = APIRouter(prefix="/admin", tags=["web-admin"])


@router.get("/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> HTMLResponse:
    users = db.query(User).all()
    return templates.TemplateResponse(
        "admin/users.html", {"request": request, "user": user, "users": users}
    )


@router.get("/audit", response_class=HTMLResponse)
async def admin_audit(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_or_auditor),
) -> HTMLResponse:
    logs = db.query(AuditLog).order_by(AuditLog.occurred_at.desc()).limit(200).all()
    return templates.TemplateResponse(
        "admin/audit.html", {"request": request, "user": user, "logs": logs}
    )
