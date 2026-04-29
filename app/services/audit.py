from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def log(
    session: Session,
    actor: User | None,
    action: str,
    target_type: str,
    target_id: str | None = None,
    payload: dict | None = None,
    actor_role_code: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        occurred_at=datetime.utcnow(),
        actor_id=actor.id if actor else None,
        actor_role_code=actor_role_code,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        payload_json=json.dumps(payload) if payload else None,
    )
    session.add(entry)
    # Intentionally NOT committing here – caller decides transaction boundary
    return entry
