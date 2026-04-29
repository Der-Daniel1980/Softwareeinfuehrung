from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth_deps import require_admin_or_auditor
from app.database import get_db
from app.models import AuditLog

router = APIRouter(prefix="/audit-log", tags=["audit"])


@router.get("")
def get_audit_log(
    db: Session = Depends(get_db),
    _user=Depends(require_admin_or_auditor),
    limit: int = 200,
    offset: int = 0,
) -> list[dict]:
    logs = (
        db.query(AuditLog)
        .order_by(AuditLog.occurred_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": entry.id,
            "occurred_at": entry.occurred_at.isoformat() if entry.occurred_at else None,
            "actor_id": entry.actor_id,
            "actor_role_code": entry.actor_role_code,
            "action": entry.action,
            "target_type": entry.target_type,
            "target_id": entry.target_id,
            "payload_json": entry.payload_json,
        }
        for entry in logs
    ]
